"""
Tests for Unit seeding functionality.

Feature 022: Unit Reference Table

Tests cover:
- Fresh database has 27 units after initialization
- Units distributed correctly across categories
- Seeding is idempotent (no duplicates)
- All expected unit codes are present
- Each unit has correct category assignment
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from src.models.base import Base
from src.models.unit import Unit
from src.services.database import seed_units, UNIT_METADATA
from src.utils.constants import WEIGHT_UNITS, VOLUME_UNITS, COUNT_UNITS, PACKAGE_UNITS


@pytest.fixture(scope="function")
def test_db():
    """Provide a clean test database for seeding tests.

    This fixture creates an in-memory SQLite database,
    patches the session factory, and cleans up afterward.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)

    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    Session = scoped_session(session_factory)

    # Monkey-patch the global session factory for tests
    import src.services.database as db_module

    original_get_session_factory = db_module.get_session_factory
    db_module.get_session_factory = lambda: Session

    yield Session

    # Cleanup
    Session.remove()
    # Feature 037 note:
    # SQLite can error during drop_all when FK cycles exist in metadata
    # (production_runs <-> recipe_snapshots). Disable FK enforcement just for teardown.
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(conn)
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
    db_module.get_session_factory = original_get_session_factory


class TestUnitSeeding:
    """Tests for unit seeding functionality (Feature 022)."""

    def test_fresh_database_has_35_units(self, test_db):
        """Test that seed_units() creates exactly 35 units."""
        # Verify database starts empty
        session = test_db()
        assert session.query(Unit).count() == 0
        session.close()

        # Seed units
        seed_units()

        # Verify 35 units created (4 weight + 9 volume + 4 count + 18 package)
        session = test_db()
        count = session.query(Unit).count()
        session.close()

        assert count == 35

    def test_units_distributed_by_category(self, test_db):
        """Test units are distributed correctly: 4 weight, 9 volume, 4 count, 18 package."""
        seed_units()

        session = test_db()
        weight_count = session.query(Unit).filter_by(category="weight").count()
        volume_count = session.query(Unit).filter_by(category="volume").count()
        count_count = session.query(Unit).filter_by(category="count").count()
        package_count = session.query(Unit).filter_by(category="package").count()
        session.close()

        assert weight_count == 4, f"Expected 4 weight units, got {weight_count}"
        assert volume_count == 9, f"Expected 9 volume units, got {volume_count}"
        assert count_count == 4, f"Expected 4 count units, got {count_count}"
        assert package_count == 18, f"Expected 18 package units, got {package_count}"

    def test_seeding_is_idempotent(self, test_db):
        """Test that running seed_units() twice doesn't create duplicates."""
        # First seed
        seed_units()

        session = test_db()
        first_count = session.query(Unit).count()
        session.close()

        # Second seed
        seed_units()

        session = test_db()
        second_count = session.query(Unit).count()
        session.close()

        assert first_count == 35
        assert second_count == 35, "Duplicate seeding created extra units"

    def test_all_weight_units_present(self, test_db):
        """Test all weight unit codes from constants are seeded."""
        seed_units()

        session = test_db()
        for code in WEIGHT_UNITS:
            unit = session.query(Unit).filter_by(code=code).first()
            assert unit is not None, f"Weight unit '{code}' not found"
            assert unit.category == "weight"
        session.close()

    def test_all_volume_units_present(self, test_db):
        """Test all volume unit codes from constants are seeded."""
        seed_units()

        session = test_db()
        for code in VOLUME_UNITS:
            unit = session.query(Unit).filter_by(code=code).first()
            assert unit is not None, f"Volume unit '{code}' not found"
            assert unit.category == "volume"
        session.close()

    def test_all_count_units_present(self, test_db):
        """Test all count unit codes from constants are seeded."""
        seed_units()

        session = test_db()
        for code in COUNT_UNITS:
            unit = session.query(Unit).filter_by(code=code).first()
            assert unit is not None, f"Count unit '{code}' not found"
            assert unit.category == "count"
        session.close()

    def test_all_package_units_present(self, test_db):
        """Test all package unit codes from constants are seeded."""
        seed_units()

        session = test_db()
        for code in PACKAGE_UNITS:
            unit = session.query(Unit).filter_by(code=code).first()
            assert unit is not None, f"Package unit '{code}' not found"
            assert unit.category == "package"
        session.close()

    def test_unit_metadata_applied_correctly(self, test_db):
        """Test that unit metadata (display_name, symbol, un_cefact_code) is applied."""
        seed_units()

        session = test_db()

        # Test a few specific units with known metadata
        oz_unit = session.query(Unit).filter_by(code="oz").first()
        assert oz_unit.display_name == "ounce"
        assert oz_unit.symbol == "oz"
        assert oz_unit.un_cefact_code == "ONZ"

        cup_unit = session.query(Unit).filter_by(code="cup").first()
        assert cup_unit.display_name == "cup"
        assert cup_unit.symbol == "cup"
        assert cup_unit.un_cefact_code is None  # cup has no UN/CEFACT code

        dozen_unit = session.query(Unit).filter_by(code="dozen").first()
        assert dozen_unit.display_name == "dozen"
        assert dozen_unit.symbol == "dz"
        assert dozen_unit.un_cefact_code == "DZN"

        session.close()

    def test_sort_order_assigned_within_category(self, test_db):
        """Test that sort_order is assigned incrementally within each category."""
        seed_units()

        session = test_db()

        # Weight units should have sort_order 0, 1, 2, 3
        weight_units = session.query(Unit).filter_by(category="weight").order_by(Unit.sort_order).all()
        for i, unit in enumerate(weight_units):
            assert unit.sort_order == i, f"Weight unit {unit.code} has sort_order {unit.sort_order}, expected {i}"

        # Volume units should have sort_order 0 through 8
        volume_units = session.query(Unit).filter_by(category="volume").order_by(Unit.sort_order).all()
        for i, unit in enumerate(volume_units):
            assert unit.sort_order == i, f"Volume unit {unit.code} has sort_order {unit.sort_order}, expected {i}"

        session.close()

    def test_unit_metadata_dictionary_complete(self):
        """Test that UNIT_METADATA has entries for all units in constants."""
        all_units = set(WEIGHT_UNITS) | set(VOLUME_UNITS) | set(COUNT_UNITS) | set(PACKAGE_UNITS)

        for code in all_units:
            assert code in UNIT_METADATA, f"Unit '{code}' missing from UNIT_METADATA dictionary"
            metadata = UNIT_METADATA[code]
            assert len(metadata) == 3, f"Unit '{code}' metadata should have 3 elements (display_name, symbol, un_cefact_code)"
