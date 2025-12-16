"""
Tests for Unit Service functions.

Feature 022: Unit Reference Table

Tests cover:
- get_all_units() returns correct count and order
- get_units_by_category() filters correctly
- get_units_for_dropdown() formats with category headers
- get_unit_by_code() retrieves single unit
- is_valid_unit() validates unit codes
- Session parameter handling
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from src.models.base import Base
from src.models.unit import Unit
from src.services.database import seed_units
from src.services.unit_service import (
    get_all_units,
    get_units_by_category,
    get_units_for_dropdown,
    get_unit_by_code,
    is_valid_unit,
)


@pytest.fixture(scope="function")
def test_db():
    """Provide a clean test database with seeded units.

    This fixture creates an in-memory SQLite database,
    seeds the units, patches the session factory, and cleans up afterward.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)

    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    Session = scoped_session(session_factory)

    # Monkey-patch the global session factory for tests
    import src.services.database as db_module

    original_get_session_factory = db_module.get_session_factory
    db_module.get_session_factory = lambda: Session

    # Seed units
    seed_units()

    yield Session

    # Cleanup
    Session.remove()
    Base.metadata.drop_all(engine)
    db_module.get_session_factory = original_get_session_factory


class TestGetAllUnits:
    """Tests for get_all_units() function."""

    def test_returns_27_units(self, test_db):
        """Test that get_all_units returns all 27 units."""
        units = get_all_units()
        assert len(units) == 27

    def test_returns_unit_objects(self, test_db):
        """Test that get_all_units returns Unit objects."""
        units = get_all_units()
        assert all(isinstance(u, Unit) for u in units)

    def test_units_ordered_by_category_then_sort_order(self, test_db):
        """Test that units are ordered by category, then sort_order."""
        units = get_all_units()

        # Group by category and verify sort_order within each group
        current_category = None
        current_sort_order = -1

        for unit in units:
            if unit.category != current_category:
                # New category - reset sort_order tracking
                current_category = unit.category
                current_sort_order = unit.sort_order
            else:
                # Same category - sort_order should be increasing
                assert unit.sort_order >= current_sort_order, (
                    f"Units not ordered by sort_order within category {unit.category}"
                )
                current_sort_order = unit.sort_order

    def test_accepts_session_parameter(self, test_db):
        """Test that get_all_units accepts and uses session parameter."""
        session = test_db()
        units = get_all_units(session=session)
        assert len(units) == 27
        session.close()


class TestGetUnitsByCategory:
    """Tests for get_units_by_category() function."""

    def test_weight_category_returns_4_units(self, test_db):
        """Test that weight category has 4 units."""
        units = get_units_by_category("weight")
        assert len(units) == 4

    def test_volume_category_returns_9_units(self, test_db):
        """Test that volume category has 9 units."""
        units = get_units_by_category("volume")
        assert len(units) == 9

    def test_count_category_returns_4_units(self, test_db):
        """Test that count category has 4 units."""
        units = get_units_by_category("count")
        assert len(units) == 4

    def test_package_category_returns_10_units(self, test_db):
        """Test that package category has 10 units."""
        units = get_units_by_category("package")
        assert len(units) == 10

    def test_all_returned_units_have_correct_category(self, test_db):
        """Test that all returned units have the requested category."""
        for category in ["weight", "volume", "count", "package"]:
            units = get_units_by_category(category)
            assert all(u.category == category for u in units)

    def test_units_ordered_by_sort_order(self, test_db):
        """Test that units within a category are ordered by sort_order."""
        units = get_units_by_category("weight")
        sort_orders = [u.sort_order for u in units]
        assert sort_orders == sorted(sort_orders)

    def test_invalid_category_returns_empty_list(self, test_db):
        """Test that invalid category returns empty list."""
        units = get_units_by_category("invalid")
        assert len(units) == 0

    def test_accepts_session_parameter(self, test_db):
        """Test that get_units_by_category accepts and uses session parameter."""
        session = test_db()
        units = get_units_by_category("weight", session=session)
        assert len(units) == 4
        session.close()


class TestGetUnitsForDropdown:
    """Tests for get_units_for_dropdown() function."""

    def test_single_category_starts_with_header(self, test_db):
        """Test that dropdown list starts with category header."""
        result = get_units_for_dropdown(["weight"])
        assert result[0] == "-- Weight --"

    def test_single_category_contains_unit_codes(self, test_db):
        """Test that dropdown list contains unit codes."""
        result = get_units_for_dropdown(["weight"])
        # Should be: ["-- Weight --", "oz", "lb", "g", "kg"]
        assert "oz" in result
        assert "lb" in result
        assert "g" in result
        assert "kg" in result

    def test_single_category_has_correct_count(self, test_db):
        """Test that single category has header + 4 units = 5 items."""
        result = get_units_for_dropdown(["weight"])
        assert len(result) == 5  # 1 header + 4 units

    def test_multiple_categories_have_multiple_headers(self, test_db):
        """Test that multiple categories have multiple headers."""
        result = get_units_for_dropdown(["weight", "volume"])
        headers = [item for item in result if item.startswith("--")]
        assert len(headers) == 2
        assert "-- Weight --" in headers
        assert "-- Volume --" in headers

    def test_multiple_categories_have_correct_count(self, test_db):
        """Test that weight + volume = 2 headers + 4 + 9 = 15 items."""
        result = get_units_for_dropdown(["weight", "volume"])
        assert len(result) == 15  # 2 headers + 4 weight + 9 volume

    def test_all_categories_dropdown(self, test_db):
        """Test dropdown with all categories."""
        result = get_units_for_dropdown(["weight", "volume", "count", "package"])
        # 4 headers + 27 units = 31 items
        assert len(result) == 31

    def test_returns_strings_not_objects(self, test_db):
        """Test that dropdown returns strings, not Unit objects."""
        result = get_units_for_dropdown(["weight"])
        assert all(isinstance(item, str) for item in result)

    def test_category_order_preserved(self, test_db):
        """Test that categories appear in the order specified."""
        result = get_units_for_dropdown(["volume", "weight"])
        # Volume should come before Weight
        volume_idx = result.index("-- Volume --")
        weight_idx = result.index("-- Weight --")
        assert volume_idx < weight_idx

    def test_empty_categories_returns_empty_list(self, test_db):
        """Test that empty categories list returns empty result."""
        result = get_units_for_dropdown([])
        assert len(result) == 0

    def test_accepts_session_parameter(self, test_db):
        """Test that get_units_for_dropdown accepts and uses session parameter."""
        session = test_db()
        result = get_units_for_dropdown(["weight"], session=session)
        assert len(result) == 5
        session.close()


class TestGetUnitByCode:
    """Tests for get_unit_by_code() function."""

    def test_finds_existing_unit(self, test_db):
        """Test that existing unit is found."""
        unit = get_unit_by_code("oz")
        assert unit is not None
        assert unit.code == "oz"
        assert unit.display_name == "ounce"

    def test_returns_none_for_nonexistent_code(self, test_db):
        """Test that nonexistent code returns None."""
        unit = get_unit_by_code("nonexistent")
        assert unit is None

    def test_accepts_session_parameter(self, test_db):
        """Test that get_unit_by_code accepts and uses session parameter."""
        session = test_db()
        unit = get_unit_by_code("cup", session=session)
        assert unit is not None
        assert unit.code == "cup"
        session.close()


class TestIsValidUnit:
    """Tests for is_valid_unit() function."""

    def test_valid_unit_returns_true(self, test_db):
        """Test that valid unit code returns True."""
        assert is_valid_unit("oz") is True
        assert is_valid_unit("cup") is True
        assert is_valid_unit("each") is True
        assert is_valid_unit("bag") is True

    def test_invalid_unit_returns_false(self, test_db):
        """Test that invalid unit code returns False."""
        assert is_valid_unit("invalid") is False
        assert is_valid_unit("") is False
        assert is_valid_unit("ounce") is False  # display_name, not code

    def test_accepts_session_parameter(self, test_db):
        """Test that is_valid_unit accepts and uses session parameter."""
        session = test_db()
        assert is_valid_unit("oz", session=session) is True
        assert is_valid_unit("invalid", session=session) is False
        session.close()
