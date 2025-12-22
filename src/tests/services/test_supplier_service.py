"""Tests for Supplier Service (Feature 027).

Tests cover:
- Create supplier with validation
- Get supplier by ID and UUID
- Get all suppliers (active/inactive filtering)
- Get active suppliers for dropdowns
- Update supplier attributes
- Deactivate supplier with product cascade (FR-009)
- Reactivate supplier
- Delete supplier (with/without purchases)
- Error handling for not found cases
"""

import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models.supplier import Supplier
from src.models.ingredient import Ingredient
from src.models.product import Product
from src.models.purchase import Purchase
from src.services import supplier_service
from src.services.exceptions import SupplierNotFoundError


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


class TestCreateSupplier:
    """Tests for create_supplier function."""

    def test_create_supplier_success(self, session):
        """Test creating a supplier with valid data."""
        result = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        assert result["name"] == "Costco"
        assert result["city"] == "Issaquah"
        assert result["state"] == "WA"
        assert result["zip_code"] == "98027"
        assert result["is_active"] is True
        assert "id" in result
        assert "uuid" in result

    def test_create_supplier_with_optional_fields(self, session):
        """Test creating a supplier with all optional fields."""
        result = supplier_service.create_supplier(
            name="Wegmans",
            city="Rochester",
            state="NY",
            zip_code="14624",
            street_address="123 Main St",
            notes="Great bakery selection",
            session=session,
        )

        assert result["street_address"] == "123 Main St"
        assert result["notes"] == "Great bakery selection"

    def test_create_supplier_normalizes_state(self, session):
        """Test that state is uppercased."""
        result = supplier_service.create_supplier(
            name="Test Store",
            city="Boston",
            state="ma",  # lowercase
            zip_code="02101",
            session=session,
        )

        assert result["state"] == "MA"

    def test_create_supplier_validates_state_length(self, session):
        """Test that state must be 2 characters."""
        with pytest.raises(ValueError) as exc_info:
            supplier_service.create_supplier(
                name="Test Store",
                city="Boston",
                state="MAS",  # Too long
                zip_code="02101",
                session=session,
            )

        assert "2-letter code" in str(exc_info.value)

    def test_create_supplier_validates_state_too_short(self, session):
        """Test that single character state is rejected."""
        with pytest.raises(ValueError) as exc_info:
            supplier_service.create_supplier(
                name="Test Store",
                city="Boston",
                state="M",  # Too short
                zip_code="02101",
                session=session,
            )

        assert "2-letter code" in str(exc_info.value)


class TestGetSupplier:
    """Tests for get_supplier and get_supplier_by_uuid functions."""

    def test_get_supplier_by_id(self, session):
        """Test retrieving supplier by ID."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        result = supplier_service.get_supplier(created["id"], session=session)

        assert result is not None
        assert result["name"] == "Costco"

    def test_get_supplier_not_found(self, session):
        """Test that get_supplier returns None for missing ID."""
        result = supplier_service.get_supplier(999, session=session)
        assert result is None

    def test_get_supplier_by_uuid(self, session):
        """Test retrieving supplier by UUID."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        result = supplier_service.get_supplier_by_uuid(created["uuid"], session=session)

        assert result is not None
        assert result["name"] == "Costco"
        assert result["id"] == created["id"]

    def test_get_supplier_by_uuid_not_found(self, session):
        """Test that get_supplier_by_uuid returns None for missing UUID."""
        result = supplier_service.get_supplier_by_uuid(
            "00000000-0000-0000-0000-000000000000",
            session=session,
        )
        assert result is None

    def test_get_supplier_or_raise_success(self, session):
        """Test get_supplier_or_raise returns supplier."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        result = supplier_service.get_supplier_or_raise(created["id"], session=session)

        assert result["name"] == "Costco"

    def test_get_supplier_or_raise_not_found(self, session):
        """Test get_supplier_or_raise raises exception."""
        with pytest.raises(SupplierNotFoundError) as exc_info:
            supplier_service.get_supplier_or_raise(999, session=session)

        assert exc_info.value.supplier_id == 999


class TestGetAllSuppliers:
    """Tests for get_all_suppliers and get_active_suppliers functions."""

    def test_get_all_suppliers_active_only(self, session):
        """Test getting only active suppliers."""
        # Create active supplier
        supplier_service.create_supplier(
            name="Active Store",
            city="Boston",
            state="MA",
            zip_code="02101",
            session=session,
        )

        # Create and deactivate another supplier
        inactive = supplier_service.create_supplier(
            name="Inactive Store",
            city="Boston",
            state="MA",
            zip_code="02102",
            session=session,
        )
        supplier_service.deactivate_supplier(inactive["id"], session=session)

        results = supplier_service.get_all_suppliers(include_inactive=False, session=session)

        assert len(results) == 1
        assert results[0]["name"] == "Active Store"

    def test_get_all_suppliers_includes_inactive(self, session):
        """Test getting all suppliers including inactive."""
        supplier_service.create_supplier(
            name="Active Store",
            city="Boston",
            state="MA",
            zip_code="02101",
            session=session,
        )

        inactive = supplier_service.create_supplier(
            name="Inactive Store",
            city="Boston",
            state="MA",
            zip_code="02102",
            session=session,
        )
        supplier_service.deactivate_supplier(inactive["id"], session=session)

        results = supplier_service.get_all_suppliers(include_inactive=True, session=session)

        assert len(results) == 2

    def test_get_all_suppliers_sorted_by_name(self, session):
        """Test that suppliers are sorted by name."""
        supplier_service.create_supplier(
            name="Zebra Store", city="A", state="MA", zip_code="02101", session=session
        )
        supplier_service.create_supplier(
            name="Alpha Store", city="B", state="MA", zip_code="02102", session=session
        )
        supplier_service.create_supplier(
            name="Middle Store", city="C", state="MA", zip_code="02103", session=session
        )

        results = supplier_service.get_all_suppliers(session=session)

        assert results[0]["name"] == "Alpha Store"
        assert results[1]["name"] == "Middle Store"
        assert results[2]["name"] == "Zebra Store"

    def test_get_active_suppliers(self, session):
        """Test get_active_suppliers convenience method."""
        supplier_service.create_supplier(
            name="Active Store",
            city="Boston",
            state="MA",
            zip_code="02101",
            session=session,
        )

        inactive = supplier_service.create_supplier(
            name="Inactive Store",
            city="Boston",
            state="MA",
            zip_code="02102",
            session=session,
        )
        supplier_service.deactivate_supplier(inactive["id"], session=session)

        results = supplier_service.get_active_suppliers(session=session)

        assert len(results) == 1
        assert all(s["is_active"] for s in results)


class TestUpdateSupplier:
    """Tests for update_supplier function."""

    def test_update_supplier_single_field(self, session):
        """Test updating a single field."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        result = supplier_service.update_supplier(
            created["id"],
            name="Costco Business Center",
            session=session,
        )

        assert result["name"] == "Costco Business Center"
        assert result["city"] == "Issaquah"  # Unchanged

    def test_update_supplier_multiple_fields(self, session):
        """Test updating multiple fields."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        result = supplier_service.update_supplier(
            created["id"],
            name="New Name",
            city="New City",
            notes="New notes",
            session=session,
        )

        assert result["name"] == "New Name"
        assert result["city"] == "New City"
        assert result["notes"] == "New notes"

    def test_update_supplier_normalizes_state(self, session):
        """Test that state is uppercased on update."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        result = supplier_service.update_supplier(
            created["id"],
            state="ca",  # lowercase
            session=session,
        )

        assert result["state"] == "CA"

    def test_update_supplier_validates_state(self, session):
        """Test that invalid state is rejected on update."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        with pytest.raises(ValueError) as exc_info:
            supplier_service.update_supplier(
                created["id"],
                state="WAA",  # Too long
                session=session,
            )

        assert "2-letter code" in str(exc_info.value)

    def test_update_supplier_not_found(self, session):
        """Test updating non-existent supplier raises error."""
        with pytest.raises(SupplierNotFoundError) as exc_info:
            supplier_service.update_supplier(999, name="Test", session=session)

        assert exc_info.value.supplier_id == 999


class TestDeactivateSupplier:
    """Tests for deactivate_supplier function."""

    def test_deactivate_supplier_success(self, session):
        """Test deactivating a supplier."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        result = supplier_service.deactivate_supplier(created["id"], session=session)

        assert result["is_active"] is False

    def test_deactivate_supplier_clears_product_references(self, session, test_ingredient):
        """Test that deactivation clears product.preferred_supplier_id (FR-009)."""
        # Create supplier
        supplier = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        # Create product with preferred supplier
        product = Product(
            ingredient_id=test_ingredient.id,
            product_name="Test Product",
            package_unit="lb",
            package_unit_quantity=5.0,
            preferred_supplier_id=supplier["id"],
        )
        session.add(product)
        session.flush()

        assert product.preferred_supplier_id == supplier["id"]

        # Deactivate supplier
        supplier_service.deactivate_supplier(supplier["id"], session=session)

        # Verify product reference was cleared
        session.refresh(product)
        assert product.preferred_supplier_id is None

    def test_deactivate_supplier_clears_multiple_products(self, session, test_ingredient):
        """Test that deactivation clears all affected products."""
        supplier = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        # Create multiple products with same preferred supplier
        products = []
        for i in range(3):
            product = Product(
                ingredient_id=test_ingredient.id,
                product_name=f"Test Product {i}",
                package_unit="lb",
                package_unit_quantity=5.0,
                preferred_supplier_id=supplier["id"],
            )
            session.add(product)
            products.append(product)
        session.flush()

        # Deactivate supplier
        supplier_service.deactivate_supplier(supplier["id"], session=session)

        # Verify all product references were cleared
        for product in products:
            session.refresh(product)
            assert product.preferred_supplier_id is None

    def test_deactivate_supplier_not_found(self, session):
        """Test deactivating non-existent supplier raises error."""
        with pytest.raises(SupplierNotFoundError):
            supplier_service.deactivate_supplier(999, session=session)


class TestReactivateSupplier:
    """Tests for reactivate_supplier function."""

    def test_reactivate_supplier_success(self, session):
        """Test reactivating a deactivated supplier."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        # Deactivate then reactivate
        supplier_service.deactivate_supplier(created["id"], session=session)
        result = supplier_service.reactivate_supplier(created["id"], session=session)

        assert result["is_active"] is True

    def test_reactivate_supplier_not_found(self, session):
        """Test reactivating non-existent supplier raises error."""
        with pytest.raises(SupplierNotFoundError):
            supplier_service.reactivate_supplier(999, session=session)


class TestDeleteSupplier:
    """Tests for delete_supplier function."""

    def test_delete_supplier_success(self, session):
        """Test deleting a supplier with no purchases."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        result = supplier_service.delete_supplier(created["id"], session=session)

        assert result is True

        # Verify supplier is gone
        deleted = supplier_service.get_supplier(created["id"], session=session)
        assert deleted is None

    def test_delete_supplier_with_purchases_fails(self, session, test_product):
        """Test that deleting supplier with purchases raises error."""
        # Create supplier
        supplier_data = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        # Create a purchase for this supplier
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=supplier_data["id"],
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        session.flush()

        # Attempt to delete should fail
        with pytest.raises(ValueError) as exc_info:
            supplier_service.delete_supplier(supplier_data["id"], session=session)

        assert "Cannot delete supplier" in str(exc_info.value)
        assert "1 purchases" in str(exc_info.value)
        assert "Deactivate instead" in str(exc_info.value)

    def test_delete_supplier_not_found(self, session):
        """Test deleting non-existent supplier raises error."""
        with pytest.raises(SupplierNotFoundError):
            supplier_service.delete_supplier(999, session=session)
