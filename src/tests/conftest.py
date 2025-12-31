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
def sample_supplier(test_db):
    """Provide a sample supplier for tests (F028)."""
    from src.services import supplier_service

    result = supplier_service.create_supplier(
        name="Test Supplier",
        city="Boston",
        state="MA",
        zip_code="02101",
    )
    # Return object with id attribute
    class SupplierObj:
        def __init__(self, data):
            self.id = data["id"]
            self.name = data["name"]
    return SupplierObj(result)


@pytest.fixture(scope="function")
def sample_ingredient(test_db):
    """Provide a sample ingredient for tests."""
    from src.services import ingredient_service

    return ingredient_service.create_ingredient({
        "display_name": "Test Flour",
        "category": "Flour",
        # 4-field density: 1 cup = 120g (approximately 0.507 g/ml)
        "density_volume_value": 1.0,
        "density_volume_unit": "cup",
        "density_weight_value": 120.0,
        "density_weight_unit": "g",
    })


@pytest.fixture(scope="function")
def sample_product(test_db, sample_ingredient):
    """Provide a sample product for tests."""
    from src.services import product_service
    from decimal import Decimal

    return product_service.create_product(
        sample_ingredient.slug,
        {
            "brand": "Test Brand",
            "package_size": "5 lb bag",
            "package_unit": "lb",
            "package_unit_quantity": Decimal("5.0"),
            "preferred": True,
        },
    )


@pytest.fixture(scope="function")
def hierarchy_ingredients(test_db):
    """Provide a sample ingredient hierarchy for testing leaf-only validation.

    Creates:
    - Chocolate (level 0, root)
      - Dark Chocolate (level 1, mid-tier)
        - Semi-Sweet Chips (level 2, leaf)
        - Bittersweet Chips (level 2, leaf)
    """
    from src.models.ingredient import Ingredient

    session = test_db()

    # Root category
    chocolate = Ingredient(
        display_name="Test Chocolate",
        slug="test-chocolate",
        category="Chocolate",
        hierarchy_level=0,
        parent_ingredient_id=None,
    )
    session.add(chocolate)
    session.flush()

    # Mid-tier category
    dark_chocolate = Ingredient(
        display_name="Test Dark Chocolate",
        slug="test-dark-chocolate",
        category="Chocolate",
        hierarchy_level=1,
        parent_ingredient_id=chocolate.id,
    )
    session.add(dark_chocolate)
    session.flush()

    # Leaf ingredients
    semi_sweet = Ingredient(
        display_name="Test Semi-Sweet Chips",
        slug="test-semi-sweet-chips",
        category="Chocolate",
        hierarchy_level=2,
        parent_ingredient_id=dark_chocolate.id,
    )
    session.add(semi_sweet)

    bittersweet = Ingredient(
        display_name="Test Bittersweet Chips",
        slug="test-bittersweet-chips",
        category="Chocolate",
        hierarchy_level=2,
        parent_ingredient_id=dark_chocolate.id,
    )
    session.add(bittersweet)

    session.commit()

    class HierarchyData:
        def __init__(self, root, mid, leaf1, leaf2):
            self.root = root
            self.mid = mid
            self.leaf1 = leaf1
            self.leaf2 = leaf2

    return HierarchyData(chocolate, dark_chocolate, semi_sweet, bittersweet)
