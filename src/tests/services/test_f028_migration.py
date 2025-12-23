"""Tests for F028 migration scripts."""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from src.models.base import Base
from src.models import InventoryItem, Purchase, Supplier, Product, Ingredient
from src.services.migration.f028_migration import run_migration
from src.services.migration.f028_validation import validate_migration


# Fixtures for migration tests


@pytest.fixture(scope="function")
def test_db():
    """Provide a clean test database for each test function."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    Session = scoped_session(session_factory)

    # Monkey-patch the global session factory for tests
    import src.services.database as db_module

    original_get_session = db_module.get_session_factory
    db_module.get_session_factory = lambda: Session

    yield Session()

    Session.remove()
    Base.metadata.drop_all(engine)
    db_module.get_session_factory = original_get_session


@pytest.fixture
def test_ingredient(test_db):
    """Create a test ingredient."""
    ingredient = Ingredient(
        slug="test-flour",
        display_name="Test Flour",
        category="Baking",
    )
    test_db.add(ingredient)
    test_db.flush()
    return ingredient


@pytest.fixture
def test_product(test_db, test_ingredient):
    """Create a test product."""
    product = Product(
        ingredient_id=test_ingredient.id,
        brand="Test Brand",
        package_unit_quantity=5.0,
        package_unit="lb",
        package_type="bag",
    )
    test_db.add(product)
    test_db.flush()
    return product


@pytest.fixture
def test_product_2(test_db, test_ingredient):
    """Create a second test product."""
    product = Product(
        ingredient_id=test_ingredient.id,
        brand="Other Brand",
        package_unit_quantity=10.0,
        package_unit="lb",
        package_type="bag",
    )
    test_db.add(product)
    test_db.flush()
    return product


@pytest.fixture
def test_inventory_item_without_purchase(test_db, test_product):
    """Create inventory item without purchase_id."""
    item = InventoryItem(
        product_id=test_product.id,
        quantity=5.0,
        unit_cost=8.99,
        purchase_date=date.today() - timedelta(days=10),
    )
    test_db.add(item)
    test_db.flush()
    return item


@pytest.fixture
def test_inventory_items_without_purchases(test_db, test_product):
    """Create multiple inventory items without purchase_id."""
    items = []
    for i in range(3):
        item = InventoryItem(
            product_id=test_product.id,
            quantity=5.0 + i,
            unit_cost=8.99 + i,
            purchase_date=date.today() - timedelta(days=10 + i),
        )
        test_db.add(item)
        items.append(item)
    test_db.flush()
    return items


@pytest.fixture
def test_inventory_item_with_unit_cost(test_db, test_product):
    """Create inventory item with specific unit_cost."""
    item = InventoryItem(
        product_id=test_product.id,
        quantity=10.0,
        unit_cost=12.50,
        purchase_date=date.today() - timedelta(days=5),
    )
    test_db.add(item)
    test_db.flush()
    return item


@pytest.fixture
def test_inventory_item_without_unit_cost(test_db, test_product):
    """Create inventory item with NULL unit_cost."""
    item = InventoryItem(
        product_id=test_product.id,
        quantity=3.0,
        unit_cost=None,  # NULL
        purchase_date=date.today() - timedelta(days=7),
    )
    test_db.add(item)
    test_db.flush()
    return item


@pytest.fixture
def test_supplier(test_db):
    """Create a test supplier."""
    supplier = Supplier(
        name="Test Supplier",
        city="Boston",
        state="MA",
        zip_code="02101",
        is_active=True,
    )
    test_db.add(supplier)
    test_db.flush()
    return supplier


@pytest.fixture
def test_inventory_item_with_mismatched_purchase(test_db, test_product, test_product_2, test_supplier):
    """Create inventory item linked to purchase with different product_id."""
    # Create purchase for product_2
    purchase = Purchase(
        product_id=test_product_2.id,  # Different product
        supplier_id=test_supplier.id,
        purchase_date=date.today(),
        unit_price=Decimal("10.00"),
        quantity_purchased=1,
    )
    test_db.add(purchase)
    test_db.flush()

    # Create item linked to that purchase but with product_1's product_id
    item = InventoryItem(
        product_id=test_product.id,  # This should match purchase.product_id but doesn't
        purchase_id=purchase.id,
        quantity=5.0,
        unit_cost=10.0,
        purchase_date=date.today(),
    )
    test_db.add(item)
    test_db.flush()
    return item


class TestF028Migration:
    """Test suite for migration scripts."""

    def test_migration_creates_purchases(self, test_db, test_inventory_items_without_purchases):
        """Migration creates Purchase for each unlinked InventoryItem."""
        # Setup: items without purchase_id
        initial_count = len(test_inventory_items_without_purchases)

        # Run migration
        items_processed, purchases_created = run_migration(session=test_db)

        assert items_processed == initial_count
        assert purchases_created == initial_count

    def test_migration_uses_unknown_supplier(self, test_db, test_inventory_item_without_purchase):
        """Migrated purchases use Unknown supplier."""
        run_migration(session=test_db)

        item = test_db.query(InventoryItem).get(test_inventory_item_without_purchase.id)
        purchase = test_db.query(Purchase).get(item.purchase_id)

        assert purchase.supplier.name == "Unknown"

    def test_migration_preserves_unit_cost(self, test_db, test_inventory_item_with_unit_cost):
        """Migration uses existing unit_cost for Purchase.unit_price."""
        original_cost = test_inventory_item_with_unit_cost.unit_cost

        run_migration(session=test_db)

        item = test_db.query(InventoryItem).get(test_inventory_item_with_unit_cost.id)
        purchase = test_db.query(Purchase).get(item.purchase_id)

        assert float(purchase.unit_price) == original_cost

    def test_migration_handles_null_unit_cost(self, test_db, test_inventory_item_without_unit_cost):
        """Migration handles NULL unit_cost with $0.00 fallback."""
        run_migration(session=test_db)

        item = test_db.query(InventoryItem).get(test_inventory_item_without_unit_cost.id)
        purchase = test_db.query(Purchase).get(item.purchase_id)

        assert purchase.unit_price == Decimal("0.00")
        assert item.unit_cost == 0.0

    def test_migration_dry_run(self, test_db, test_inventory_items_without_purchases):
        """Dry run reports but doesn't modify data."""
        initial_count = len(test_inventory_items_without_purchases)
        items_processed, purchases_created = run_migration(dry_run=True, session=test_db)

        assert items_processed == initial_count
        assert purchases_created == 0

        # Verify no changes
        null_count = (
            test_db.query(InventoryItem)
            .filter(InventoryItem.purchase_id == None)  # noqa: E711
            .count()
        )
        assert null_count == items_processed

    def test_migration_idempotent(self, test_db, test_inventory_items_without_purchases):
        """Running migration twice doesn't create duplicate purchases."""
        initial_count = len(test_inventory_items_without_purchases)

        # First run
        items1, purchases1 = run_migration(session=test_db)
        assert items1 == initial_count
        assert purchases1 == initial_count

        # Second run - should find no items to migrate
        items2, purchases2 = run_migration(session=test_db)
        assert items2 == 0
        assert purchases2 == 0


class TestF028Validation:
    """Test suite for validation scripts."""

    def test_validation_passes_after_migration(self, test_db, test_inventory_items_without_purchases):
        """Validation passes after successful migration."""
        run_migration(session=test_db)

        success, report = validate_migration(session=test_db)

        assert success is True
        assert len(report["errors"]) == 0

    def test_validation_fails_with_unlinked_items(self, test_db, test_inventory_items_without_purchases):
        """Validation fails when items lack purchase_id."""
        # Don't run migration

        success, report = validate_migration(session=test_db)

        assert success is False
        assert any("NULL purchase_id" in e for e in report["errors"])

    def test_validation_detects_product_mismatch(
        self, test_db, test_inventory_item_with_mismatched_purchase
    ):
        """Validation catches product_id mismatch between item and purchase."""
        success, report = validate_migration(session=test_db)

        # This should fail due to product mismatch
        assert success is False
        assert any("product_id mismatch" in e for e in report["errors"])
