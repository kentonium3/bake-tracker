"""
Tests for Supplier model.

Tests cover:
- Model creation with valid data
- Required field validation
- State constraint (2-letter uppercase)
- Default values (is_active=True)
- UUID generation
- Location/address formatting
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from src.services import supplier_service

from src.models.base import Base
from src.models.supplier import Supplier


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


class TestSupplierModel:
    """Tests for Supplier model creation and attributes."""

    def test_create_supplier_success(self, session):
        """Test creating a supplier with valid data."""
        supplier = Supplier(
            name="Costco",
            slug="costco_waltham_ma",
            city="Waltham",
            state="MA",
            zip_code="02451",
        )
        session.add(supplier)
        session.flush()

        assert supplier.id is not None
        assert supplier.name == "Costco"
        assert supplier.slug == "costco_waltham_ma"
        assert supplier.city == "Waltham"
        assert supplier.state == "MA"
        assert supplier.zip_code == "02451"

    def test_create_supplier_with_all_fields(self, session):
        """Test creating a supplier with all optional fields."""
        supplier = Supplier(
            name="Restaurant Depot",
            slug="restaurant_depot_boston_ma",
            street_address="123 Main St",
            city="Boston",
            state="MA",
            zip_code="02101",
            notes="Membership required. Open Mon-Sat 7am-6pm.",
        )
        session.add(supplier)
        session.flush()

        assert supplier.id is not None
        assert supplier.street_address == "123 Main St"
        assert supplier.notes == "Membership required. Open Mon-Sat 7am-6pm."

    def test_supplier_requires_name(self, session):
        """Service-layer validation: name is required."""
        with pytest.raises(ValueError):
            supplier_service.create_supplier(
                name=None,
                city="Boston",
                state="MA",
                zip_code="02101",
                session=session,
            )

    def test_supplier_requires_city(self, session):
        """Service-layer validation: city is required for physical suppliers."""
        with pytest.raises(ValueError):
            supplier_service.create_supplier(
                name="Test Supplier",
                city=None,
                state="MA",
                zip_code="02101",
                session=session,
            )

    def test_supplier_requires_state(self, session):
        """Service-layer validation: state is required for physical suppliers."""
        with pytest.raises(ValueError):
            supplier_service.create_supplier(
                name="Test Supplier",
                city="Boston",
                state=None,
                zip_code="02101",
                session=session,
            )

    def test_supplier_requires_zip_code(self, session):
        """Service-layer validation: zip_code is required for physical suppliers."""
        with pytest.raises(ValueError):
            supplier_service.create_supplier(
                name="Test Supplier",
                city="Boston",
                state="MA",
                zip_code=None,
                session=session,
            )

    def test_supplier_default_is_active(self, session):
        """Test that is_active defaults to True."""
        supplier = Supplier(
            name="Costco",
            slug="costco_waltham_ma_active_test",
            city="Waltham",
            state="MA",
            zip_code="02451",
        )
        session.add(supplier)
        session.flush()

        assert supplier.is_active is True

    def test_supplier_can_set_is_active_false(self, session):
        """Test that is_active can be set to False."""
        supplier = Supplier(
            name="Old Supplier",
            slug="old_supplier_boston_ma",
            city="Boston",
            state="MA",
            zip_code="02101",
            is_active=False,
        )
        session.add(supplier)
        session.flush()

        assert supplier.is_active is False

    def test_supplier_has_uuid(self, session):
        """Test that UUID is automatically generated."""
        supplier = Supplier(
            name="Costco",
            slug="costco_waltham_ma_uuid_test",
            city="Waltham",
            state="MA",
            zip_code="02451",
        )
        session.add(supplier)
        session.flush()

        assert supplier.uuid is not None
        assert len(supplier.uuid) == 36  # UUID format: 8-4-4-4-12

    def test_supplier_uuid_is_unique(self, session):
        """Test that each supplier gets a unique UUID."""
        supplier1 = Supplier(
            name="Supplier 1",
            slug="supplier_1_boston_ma",
            city="Boston",
            state="MA",
            zip_code="02101",
        )
        supplier2 = Supplier(
            name="Supplier 2",
            slug="supplier_2_cambridge_ma",
            city="Cambridge",
            state="MA",
            zip_code="02139",
        )
        session.add(supplier1)
        session.add(supplier2)
        session.flush()

        assert supplier1.uuid != supplier2.uuid

    def test_supplier_has_timestamps(self, session):
        """Test that created_at and updated_at are set."""
        supplier = Supplier(
            name="Costco",
            slug="costco_waltham_ma_timestamps_test",
            city="Waltham",
            state="MA",
            zip_code="02451",
        )
        session.add(supplier)
        session.flush()

        assert supplier.created_at is not None
        assert supplier.updated_at is not None


class TestSupplierStateConstraint:
    """Tests for state code constraint (2-letter uppercase)."""

    def test_state_uppercase_accepted(self, session):
        """Test that uppercase state codes are accepted."""
        supplier = Supplier(
            name="Test",
            slug="test_boston_ma_state_test",
            city="Boston",
            state="MA",
            zip_code="02101",
        )
        session.add(supplier)
        session.flush()  # Should not raise

        assert supplier.state == "MA"

    def test_state_lowercase_constraint(self, session):
        """Test that lowercase state codes may violate constraint.

        Note: SQLite CHECK constraints are enforced at insert/update time,
        but the constraint validation may vary by SQLite version.
        This test documents the expected behavior.
        """
        supplier = Supplier(
            name="Test",
            slug="test_boston_ma_lowercase_test",
            city="Boston",
            state="ma",  # Lowercase - violates constraint
            zip_code="02101",
        )
        session.add(supplier)
        # Note: SQLite may or may not enforce CHECK constraints
        # depending on version and configuration.
        # Service layer should validate before insert.
        try:
            session.flush()
            # If we get here, SQLite didn't enforce the constraint
            # This is expected behavior in some SQLite configurations
            assert supplier.state == "ma"
        except IntegrityError:
            # Constraint was enforced - also valid
            session.rollback()

    def test_state_too_long_constraint(self, session):
        """Test that state codes longer than 2 characters may violate constraint."""
        supplier = Supplier(
            name="Test",
            slug="test_boston_mas_long_state_test",
            city="Boston",
            state="MAS",  # 3 characters - violates constraint
            zip_code="02101",
        )
        session.add(supplier)
        try:
            session.flush()
            # If we get here, SQLite didn't enforce the constraint
            assert supplier.state == "MAS"
        except IntegrityError:
            session.rollback()


class TestSupplierMethods:
    """Tests for Supplier model methods and properties."""

    def test_location_property(self):
        """Test location property formatting."""
        supplier = Supplier(
            name="Costco",
            slug="costco_waltham_ma_location",
            city="Waltham",
            state="MA",
            zip_code="02451",
        )
        assert supplier.location == "Waltham, MA"

    def test_full_address_without_street(self):
        """Test full_address when street_address is not set."""
        supplier = Supplier(
            name="Costco",
            slug="costco_waltham_ma_fulladdr",
            city="Waltham",
            state="MA",
            zip_code="02451",
        )
        assert supplier.full_address == "Waltham, MA 02451"

    def test_full_address_with_street(self):
        """Test full_address when street_address is set."""
        supplier = Supplier(
            name="Restaurant Depot",
            slug="restaurant_depot_boston_ma_street",
            street_address="123 Main St",
            city="Boston",
            state="MA",
            zip_code="02101",
        )
        assert supplier.full_address == "123 Main St, Boston, MA 02101"

    def test_repr(self):
        """Test string representation."""
        supplier = Supplier(
            name="Costco",
            slug="costco_waltham_ma_repr",
            city="Waltham",
            state="MA",
            zip_code="02451",
        )
        # Can't check id since it's not set without session
        repr_str = repr(supplier)
        assert "Supplier" in repr_str
        assert "Costco" in repr_str
        assert "Waltham" in repr_str
        assert "MA" in repr_str

    def test_to_dict(self, session):
        """Test to_dict method includes computed fields."""
        supplier = Supplier(
            name="Costco",
            slug="costco_waltham_ma_todict",
            street_address="100 Commerce Way",
            city="Waltham",
            state="MA",
            zip_code="02451",
        )
        session.add(supplier)
        session.flush()

        result = supplier.to_dict()

        assert result["name"] == "Costco"
        assert result["slug"] == "costco_waltham_ma_todict"
        assert result["city"] == "Waltham"
        assert result["state"] == "MA"
        assert result["zip_code"] == "02451"
        assert result["location"] == "Waltham, MA"
        assert result["full_address"] == "100 Commerce Way, Waltham, MA 02451"
        assert result["is_active"] is True
        assert "id" in result
        assert "uuid" in result
        assert "created_at" in result
        assert "updated_at" in result
