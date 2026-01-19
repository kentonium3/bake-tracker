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
    1. Creates an in-memory SQLite database with foreign keys enabled
    2. Creates all tables
    3. Provides the database to the test
    4. Drops all tables after the test completes
    """
    from sqlalchemy import event

    # Create in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Enable foreign key support in SQLite (required for CASCADE to work)
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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
    # Feature 037 note:
    # SQLite can't always drop tables cleanly when there are FK cycles
    # (production_runs <-> recipe_snapshots). Keep FK enforcement ON for tests,
    # but disable it just for teardown so drop_all can succeed deterministically.
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(conn)
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")

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

    return ingredient_service.create_ingredient(
        {
            "display_name": "Test Flour",
            "category": "Flour",
            # 4-field density: 1 cup = 120g (approximately 0.507 g/ml)
            "density_volume_value": 1.0,
            "density_volume_unit": "cup",
            "density_weight_value": 120.0,
            "density_weight_unit": "g",
        }
    )


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


@pytest.fixture(scope="function")
def sample_hierarchy_from_json(test_db):
    """Load sample hierarchy from JSON file for comprehensive testing (T042).

    Loads test_data/sample_hierarchy.json which contains:
    - 4 root categories (Chocolate, Dairy, Flours, Sugars)
    - 12 mid-tier categories
    - 32 leaf ingredients

    Returns a dict with lists of ingredients by level and a lookup by ID.
    """
    import json
    import os
    from src.models.ingredient import Ingredient

    session = test_db()

    # Find the sample_hierarchy.json file
    # Try multiple paths since test runner may have different cwd
    possible_paths = [
        "test_data/sample_hierarchy.json",
        "../test_data/sample_hierarchy.json",
        os.path.join(os.path.dirname(__file__), "../../test_data/sample_hierarchy.json"),
    ]

    data = None
    for path in possible_paths:
        try:
            with open(path) as f:
                data = json.load(f)
            break
        except FileNotFoundError:
            continue

    if data is None:
        pytest.skip("sample_hierarchy.json not found")

    records = data["records"]
    by_id = {}
    by_level = {0: [], 1: [], 2: []}

    # Sort by level to ensure parents are created before children
    sorted_records = sorted(records, key=lambda r: r.get("hierarchy_level", 2))

    # Map old IDs to new IDs (database will assign new ones)
    id_map = {}

    for r in sorted_records:
        old_id = r["id"]
        parent_id = r.get("parent_ingredient_id")

        # Map parent ID if needed
        mapped_parent_id = id_map.get(parent_id) if parent_id else None

        ingredient = Ingredient(
            slug=r["slug"],
            display_name=r["display_name"],
            category=r.get("category") or r["display_name"],  # Use display_name if no category
            hierarchy_level=r.get("hierarchy_level", 2),
            parent_ingredient_id=mapped_parent_id,
            description=r.get("description"),
        )
        session.add(ingredient)
        session.flush()  # Get the new ID

        # Store mapping
        id_map[old_id] = ingredient.id
        by_id[ingredient.id] = ingredient
        by_level[ingredient.hierarchy_level].append(ingredient)

    session.commit()

    class SampleHierarchy:
        def __init__(self, by_id, by_level, id_map):
            self.by_id = by_id
            self.by_level = by_level
            self.id_map = id_map
            self.roots = by_level[0]
            self.mid_tier = by_level[1]
            self.leaves = by_level[2]

    return SampleHierarchy(by_id, by_level, id_map)
