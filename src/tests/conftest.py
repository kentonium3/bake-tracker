"""Pytest configuration and fixtures for service layer tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from src.models.base import Base
from src.services.database import get_session_factory


@pytest.fixture(scope="function")
def test_db():
    """Provide a clean test database for each test function.

    This fixture:
    1. Creates an in-memory SQLite database
    2. Creates all tables
    3. Provides the database to the test
    4. Drops all tables after the test completes
    """
    # Create in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session factory
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    Session = scoped_session(session_factory)

    # Monkey-patch the global session factory for tests
    import src.services.database as db_module

    original_get_session = db_module.get_session_factory
    db_module.get_session_factory = lambda: Session

    # Provide database to test
    yield Session

    # Cleanup
    Session.remove()
    Base.metadata.drop_all(engine)

    # Restore original session factory
    db_module.get_session_factory = original_get_session


@pytest.fixture(scope="function")
def sample_ingredient(test_db):
    """Provide a sample ingredient for tests."""
    from src.services import ingredient_service

    return ingredient_service.create_ingredient(
        {"name": "Test Flour", "category": "Flour", "recipe_unit": "cup", "density_g_per_ml": 0.507}
    )


@pytest.fixture(scope="function")
def sample_variant(test_db, sample_ingredient):
    """Provide a sample variant for tests."""
    from src.services import variant_service
    from decimal import Decimal

    return variant_service.create_variant(
        sample_ingredient.slug,
        {
            "brand": "Test Brand",
            "package_size": "5 lb bag",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("5.0"),
            "preferred": True,
        },
    )
