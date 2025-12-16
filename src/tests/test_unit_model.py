"""
Tests for Unit model.

Feature 022: Unit Reference Table

Tests cover:
- Unit model creation with required fields
- Unique constraint on code
- Category storage
- BaseModel inheritance (id, uuid, created_at, updated_at)
- __repr__ output
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from src.models.base import Base
from src.models.unit import Unit


@pytest.fixture(scope="function")
def db_session():
    """
    Create a test database session.

    This fixture creates an in-memory database for each test,
    ensuring tests are isolated.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


class TestUnitModel:
    """Tests for Unit model (Feature 022)."""

    def test_create_unit_with_required_fields(self, db_session):
        """Test creating a unit with all required fields."""
        unit = Unit(
            code="oz",
            display_name="ounce",
            symbol="oz",
            category="weight",
            sort_order=0,
        )
        db_session.add(unit)
        db_session.commit()

        assert unit.id is not None
        assert unit.code == "oz"
        assert unit.display_name == "ounce"
        assert unit.symbol == "oz"
        assert unit.category == "weight"
        assert unit.sort_order == 0

    def test_create_unit_with_optional_un_cefact_code(self, db_session):
        """Test creating a unit with optional UN/CEFACT code."""
        unit = Unit(
            code="kg",
            display_name="kilogram",
            symbol="kg",
            category="weight",
            un_cefact_code="KGM",
            sort_order=3,
        )
        db_session.add(unit)
        db_session.commit()

        assert unit.un_cefact_code == "KGM"

    def test_unit_without_un_cefact_code(self, db_session):
        """Test that un_cefact_code is nullable."""
        unit = Unit(
            code="cup",
            display_name="cup",
            symbol="cup",
            category="volume",
            sort_order=2,
        )
        db_session.add(unit)
        db_session.commit()

        assert unit.un_cefact_code is None

    def test_unit_code_must_be_unique(self, db_session):
        """Test that unit codes are unique."""
        unit1 = Unit(
            code="oz",
            display_name="ounce",
            symbol="oz",
            category="weight",
            sort_order=0,
        )
        db_session.add(unit1)
        db_session.commit()

        unit2 = Unit(
            code="oz",  # Duplicate code
            display_name="different",
            symbol="diff",
            category="volume",
            sort_order=0,
        )
        db_session.add(unit2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_unit_category_stored_correctly(self, db_session):
        """Test that category is stored and retrieved correctly."""
        categories = ["weight", "volume", "count", "package"]

        for i, category in enumerate(categories):
            unit = Unit(
                code=f"test_{category}",
                display_name=f"Test {category}",
                symbol=f"t{category[0]}",
                category=category,
                sort_order=i,
            )
            db_session.add(unit)

        db_session.commit()

        for category in categories:
            queried = db_session.query(Unit).filter_by(code=f"test_{category}").first()
            assert queried is not None
            assert queried.category == category

    def test_unit_inherits_basemodel_id(self, db_session):
        """Test that Unit inherits id from BaseModel."""
        unit = Unit(
            code="lb",
            display_name="pound",
            symbol="lb",
            category="weight",
            sort_order=1,
        )
        db_session.add(unit)
        db_session.commit()

        assert unit.id is not None
        assert isinstance(unit.id, int)
        assert unit.id > 0

    def test_unit_inherits_basemodel_uuid(self, db_session):
        """Test that Unit inherits uuid from BaseModel."""
        unit = Unit(
            code="g",
            display_name="gram",
            symbol="g",
            category="weight",
            sort_order=2,
        )
        db_session.add(unit)
        db_session.commit()

        assert unit.uuid is not None
        assert len(unit.uuid) == 36  # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

    def test_unit_inherits_basemodel_timestamps(self, db_session):
        """Test that Unit inherits created_at and updated_at from BaseModel."""
        unit = Unit(
            code="ml",
            display_name="milliliter",
            symbol="ml",
            category="volume",
            sort_order=3,
        )
        db_session.add(unit)
        db_session.commit()

        assert unit.created_at is not None
        assert unit.updated_at is not None
        assert isinstance(unit.created_at, datetime)
        assert isinstance(unit.updated_at, datetime)

    def test_unit_repr(self, db_session):
        """Test Unit __repr__ returns expected string."""
        unit = Unit(
            code="tsp",
            display_name="teaspoon",
            symbol="tsp",
            category="volume",
            sort_order=0,
        )
        db_session.add(unit)
        db_session.commit()

        expected = "Unit(code='tsp', category='volume')"
        assert repr(unit) == expected

    def test_unit_sort_order_default(self, db_session):
        """Test that sort_order defaults to 0."""
        unit = Unit(
            code="each",
            display_name="each",
            symbol="ea",
            category="count",
        )
        db_session.add(unit)
        db_session.commit()

        assert unit.sort_order == 0

    def test_query_units_by_category(self, db_session):
        """Test querying units by category."""
        # Add units from different categories
        units_data = [
            ("oz", "ounce", "oz", "weight", 0),
            ("lb", "pound", "lb", "weight", 1),
            ("cup", "cup", "cup", "volume", 0),
            ("ml", "milliliter", "ml", "volume", 1),
            ("each", "each", "ea", "count", 0),
        ]

        for code, display_name, symbol, category, sort_order in units_data:
            unit = Unit(
                code=code,
                display_name=display_name,
                symbol=symbol,
                category=category,
                sort_order=sort_order,
            )
            db_session.add(unit)

        db_session.commit()

        # Query by category
        weight_units = db_session.query(Unit).filter_by(category="weight").all()
        volume_units = db_session.query(Unit).filter_by(category="volume").all()
        count_units = db_session.query(Unit).filter_by(category="count").all()

        assert len(weight_units) == 2
        assert len(volume_units) == 2
        assert len(count_units) == 1
