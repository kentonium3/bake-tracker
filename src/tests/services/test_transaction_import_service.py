"""
Tests for transaction_import_service purchase and adjustment import functionality.

Purchase Import Tests (WP04) cover:
- import_purchases() creates Purchase and InventoryItem records
- Positive quantity validation (rejects negative/zero)
- Product slug resolution with clear errors
- Duplicate detection (product + date + price)
- Weighted average cost updates
- Dry run mode (no commits)
- Atomic transactions (rollback on failure)

Adjustment Import Tests (WP05) cover:
- import_adjustments() decreases inventory quantities
- Negative quantity validation (rejects positive/zero)
- reason_code validation (required, must be in allowed list)
- FIFO inventory selection (oldest items depleted first)
- Prevents adjustments exceeding available inventory
- Creates InventoryDepletion audit records
- Dry run mode (validates without committing)

Feature 049: Import/Export System Phase 1 - WP04 & WP05 Unit Tests
"""

import json
import os
import pytest
import tempfile
from datetime import date, timedelta
from decimal import Decimal

from src.models.ingredient import Ingredient
from src.models.product import Product
from src.models.purchase import Purchase
from src.models.inventory_item import InventoryItem
from src.models.inventory_depletion import InventoryDepletion
from src.models.supplier import Supplier
from src.services.transaction_import_service import (
    import_purchases,
    import_adjustments,
    ALLOWED_REASON_CODES,
    _parse_datetime,
    _is_duplicate_purchase,
    _resolve_supplier,
)
from src.services.database import session_scope


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def cleanup_transaction_data(test_db):
    """Cleanup transaction test data after each test."""
    yield
    with session_scope() as session:
        # Delete in reverse dependency order
        session.query(InventoryDepletion).delete(synchronize_session=False)
        session.query(InventoryItem).delete(synchronize_session=False)
        session.query(Purchase).delete(synchronize_session=False)
        session.query(Product).delete(synchronize_session=False)
        session.query(Ingredient).delete(synchronize_session=False)
        session.query(Supplier).delete(synchronize_session=False)


@pytest.fixture
def sample_ingredient_for_purchase(test_db):
    """Create a sample ingredient for purchase tests."""
    with session_scope() as session:
        ingredient = Ingredient(
            slug="all_purpose_flour",
            display_name="All-Purpose Flour",
            category="Flour",
        )
        session.add(ingredient)
        session.flush()
        return {
            "id": ingredient.id,
            "slug": ingredient.slug,
            "display_name": ingredient.display_name,
        }


@pytest.fixture
def sample_product_for_purchase(test_db, sample_ingredient_for_purchase):
    """Create a sample product for purchase tests."""
    with session_scope() as session:
        product = Product(
            ingredient_id=sample_ingredient_for_purchase["id"],
            brand="King Arthur",
            product_name="All-Purpose Flour",
            package_size="5 lb",
            package_type="bag",
            package_unit="lb",
            package_unit_quantity=5.0,
        )
        session.add(product)
        session.flush()
        # Build composite slug: ingredient_slug:brand:qty:unit
        ingredient_slug = sample_ingredient_for_purchase["slug"]
        composite_slug = f"{ingredient_slug}:King Arthur:5.0:lb"
        return {
            "id": product.id,
            "slug": composite_slug,  # Composite slug for _resolve_product_by_slug
            "brand": product.brand,
            "ingredient_id": product.ingredient_id,
        }


@pytest.fixture
def sample_supplier_for_purchase(test_db):
    """Create a sample supplier for purchase tests."""
    with session_scope() as session:
        supplier = Supplier(
            name="Costco",
            city="Waltham",
            state="MA",
            zip_code="02451",
        )
        session.add(supplier)
        session.flush()
        return {"id": supplier.id, "name": supplier.name}


@pytest.fixture
def create_purchase_file():
    """Factory fixture to create temporary JSON files for testing."""
    created_files = []

    def _create_file(data: dict) -> str:
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        created_files.append(path)
        return path

    yield _create_file

    # Cleanup
    for path in created_files:
        if os.path.exists(path):
            os.remove(path)


# ============================================================================
# Test: import_purchases creates records
# ============================================================================


class TestImportPurchasesCreatesRecords:
    """Test that import_purchases creates Purchase and InventoryItem records."""

    def test_import_purchases_creates_purchase_record(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        create_purchase_file,
    ):
        """Verify Purchase record is created with correct data."""
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "created_at": "2026-01-12T14:30:00Z",
            "source": "bt_mobile",
            "purchases": [
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-12T14:15:23Z",
                    "unit_price": 7.99,
                    "quantity_purchased": 2,
                    "notes": "Weekly shopping",
                }
            ],
        })

        result = import_purchases(file_path)

        # Verify success count
        assert result.successful == 1
        assert result.failed == 0
        assert result.skipped == 0

        # Verify Purchase record in database
        with session_scope() as session:
            purchase = session.query(Purchase).first()
            assert purchase is not None
            assert purchase.product_id == sample_product_for_purchase["id"]
            assert purchase.purchase_date == date(2026, 1, 12)
            assert float(purchase.unit_price) == 7.99
            assert purchase.quantity_purchased == 2
            assert purchase.notes == "Weekly shopping"

    def test_import_purchases_creates_inventory_item(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        create_purchase_file,
    ):
        """Verify InventoryItem record is created and linked to Purchase."""
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "purchases": [
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-12T14:15:23Z",
                    "unit_price": 7.99,
                    "quantity_purchased": 2,
                }
            ],
        })

        result = import_purchases(file_path)

        assert result.successful == 1

        # Verify InventoryItem record in database
        with session_scope() as session:
            inventory_item = session.query(InventoryItem).first()
            assert inventory_item is not None
            assert inventory_item.product_id == sample_product_for_purchase["id"]
            assert inventory_item.quantity == 2.0
            assert inventory_item.unit_cost == 7.99
            assert inventory_item.purchase_date == date(2026, 1, 12)

            # Verify linked to purchase
            purchase = session.query(Purchase).first()
            assert inventory_item.purchase_id == purchase.id

    def test_import_multiple_purchases(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        create_purchase_file,
    ):
        """Verify multiple purchases in one file are all processed."""
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "purchases": [
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-10T10:00:00Z",
                    "unit_price": 7.99,
                    "quantity_purchased": 1,
                },
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-11T11:00:00Z",
                    "unit_price": 8.49,
                    "quantity_purchased": 2,
                },
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-12T12:00:00Z",
                    "unit_price": 7.49,
                    "quantity_purchased": 3,
                },
            ],
        })

        result = import_purchases(file_path)

        assert result.successful == 3
        assert result.failed == 0

        with session_scope() as session:
            purchases = session.query(Purchase).all()
            inventory_items = session.query(InventoryItem).all()
            assert len(purchases) == 3
            assert len(inventory_items) == 3


# ============================================================================
# Test: Positive quantity validation
# ============================================================================


class TestImportPurchasesRejectsNegativeQuantity:
    """Test that purchases with non-positive quantities are rejected."""

    def test_import_rejects_negative_quantity(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        create_purchase_file,
    ):
        """Verify negative quantity is rejected with proper error."""
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "purchases": [
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-12T14:15:23Z",
                    "unit_price": 7.99,
                    "quantity_purchased": -2,
                }
            ],
        })

        result = import_purchases(file_path)

        assert result.successful == 0
        assert result.failed == 1
        assert len(result.errors) == 1
        assert "Invalid quantity" in result.errors[0]["message"]
        assert "positive quantities" in result.errors[0]["message"]

    def test_import_rejects_zero_quantity(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        create_purchase_file,
    ):
        """Verify zero quantity is rejected with proper error."""
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "purchases": [
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-12T14:15:23Z",
                    "unit_price": 7.99,
                    "quantity_purchased": 0,
                }
            ],
        })

        result = import_purchases(file_path)

        assert result.successful == 0
        assert result.failed == 1
        assert "Invalid quantity 0" in result.errors[0]["message"]


# ============================================================================
# Test: Product slug resolution
# ============================================================================


class TestImportPurchasesRejectsUnknownProduct:
    """Test that unknown product_slug results in proper error."""

    def test_import_rejects_unknown_product(
        self,
        test_db,
        cleanup_transaction_data,
        create_purchase_file,
    ):
        """Verify unknown product slug produces actionable error."""
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "purchases": [
                {
                    "product_slug": "nonexistent_product_slug",
                    "purchased_at": "2026-01-12T14:15:23Z",
                    "unit_price": 7.99,
                    "quantity_purchased": 1,
                }
            ],
        })

        result = import_purchases(file_path)

        assert result.successful == 0
        assert result.failed == 1
        assert len(result.errors) == 1
        assert "not found" in result.errors[0]["message"]
        assert "nonexistent_product_slug" in result.errors[0]["message"]
        assert result.errors[0].get("suggestion") is not None

    def test_import_rejects_missing_product_slug(
        self,
        test_db,
        cleanup_transaction_data,
        create_purchase_file,
    ):
        """Verify missing product_slug field produces proper error."""
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "purchases": [
                {
                    "purchased_at": "2026-01-12T14:15:23Z",
                    "unit_price": 7.99,
                    "quantity_purchased": 1,
                }
            ],
        })

        result = import_purchases(file_path)

        assert result.successful == 0
        assert result.failed == 1
        assert "Missing product_slug" in result.errors[0]["message"]


# ============================================================================
# Test: Duplicate detection
# ============================================================================


class TestImportPurchasesSkipsDuplicates:
    """Test that duplicate purchases are detected and skipped."""

    def test_import_skips_duplicate_purchase(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_supplier_for_purchase,
        create_purchase_file,
    ):
        """Verify duplicate purchase (same product, date, price) is skipped."""
        # Create existing purchase
        with session_scope() as session:
            existing_purchase = Purchase(
                product_id=sample_product_for_purchase["id"],
                supplier_id=sample_supplier_for_purchase["id"],
                purchase_date=date(2026, 1, 12),
                unit_price=Decimal("7.99"),
                quantity_purchased=2,
            )
            session.add(existing_purchase)

        # Try to import same purchase
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "purchases": [
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-12T14:15:23Z",
                    "unit_price": 7.99,
                    "quantity_purchased": 1,  # Different quantity
                }
            ],
        })

        result = import_purchases(file_path)

        # Should be skipped, not failed
        assert result.successful == 0
        assert result.skipped == 1
        assert result.failed == 0
        assert len(result.warnings) == 1
        assert "Duplicate" in result.warnings[0]["message"]

    def test_import_allows_same_product_different_date(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_supplier_for_purchase,
        create_purchase_file,
    ):
        """Verify same product with different date is NOT a duplicate."""
        # Create existing purchase
        with session_scope() as session:
            existing_purchase = Purchase(
                product_id=sample_product_for_purchase["id"],
                supplier_id=sample_supplier_for_purchase["id"],
                purchase_date=date(2026, 1, 12),
                unit_price=Decimal("7.99"),
                quantity_purchased=2,
            )
            session.add(existing_purchase)

        # Import with different date
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "purchases": [
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-13T14:15:23Z",  # Different date
                    "unit_price": 7.99,
                    "quantity_purchased": 1,
                }
            ],
        })

        result = import_purchases(file_path)

        assert result.successful == 1
        assert result.skipped == 0

    def test_import_allows_same_product_different_price(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_supplier_for_purchase,
        create_purchase_file,
    ):
        """Verify same product/date with different price is NOT a duplicate."""
        # Create existing purchase
        with session_scope() as session:
            existing_purchase = Purchase(
                product_id=sample_product_for_purchase["id"],
                supplier_id=sample_supplier_for_purchase["id"],
                purchase_date=date(2026, 1, 12),
                unit_price=Decimal("7.99"),
                quantity_purchased=2,
            )
            session.add(existing_purchase)

        # Import with different price
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "purchases": [
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-12T14:15:23Z",
                    "unit_price": 8.49,  # Different price
                    "quantity_purchased": 1,
                }
            ],
        })

        result = import_purchases(file_path)

        assert result.successful == 1
        assert result.skipped == 0


# ============================================================================
# Test: Dry run mode
# ============================================================================


class TestImportPurchasesDryRun:
    """Test dry_run mode validates without committing."""

    def test_dry_run_no_commit(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        create_purchase_file,
    ):
        """Verify dry_run=True does not create records in database."""
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "purchases": [
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-12T14:15:23Z",
                    "unit_price": 7.99,
                    "quantity_purchased": 2,
                }
            ],
        })

        result = import_purchases(file_path, dry_run=True)

        # Should report success from validation perspective
        assert result.successful == 1
        assert result.failed == 0

        # But no records in database
        with session_scope() as session:
            purchases = session.query(Purchase).all()
            inventory_items = session.query(InventoryItem).all()
            assert len(purchases) == 0
            assert len(inventory_items) == 0


# ============================================================================
# Test: Supplier resolution
# ============================================================================


class TestImportPurchasesSupplierResolution:
    """Test supplier resolution during import."""

    def test_import_resolves_existing_supplier(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_supplier_for_purchase,
        create_purchase_file,
    ):
        """Verify existing supplier is found and linked."""
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "purchases": [
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-12T14:15:23Z",
                    "unit_price": 7.99,
                    "quantity_purchased": 1,
                    "supplier": "Costco",  # Matches sample_supplier_for_purchase
                }
            ],
        })

        result = import_purchases(file_path)

        assert result.successful == 1

        with session_scope() as session:
            purchase = session.query(Purchase).first()
            assert purchase.supplier_id == sample_supplier_for_purchase["id"]

    def test_import_creates_new_supplier(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        create_purchase_file,
    ):
        """Verify new supplier is created if not found."""
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "purchases": [
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-12T14:15:23Z",
                    "unit_price": 7.99,
                    "quantity_purchased": 1,
                    "supplier": "New Store Name",
                }
            ],
        })

        result = import_purchases(file_path)

        assert result.successful == 1

        with session_scope() as session:
            # Verify supplier was created
            supplier = session.query(Supplier).filter_by(name="New Store Name").first()
            assert supplier is not None

            # Verify purchase linked to new supplier
            purchase = session.query(Purchase).first()
            assert purchase.supplier_id == supplier.id

    def test_import_uses_default_supplier_from_header(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        create_purchase_file,
    ):
        """Verify default supplier from file header is used."""
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "supplier": "Header Supplier",  # Default supplier in header
            "purchases": [
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-12T14:15:23Z",
                    "unit_price": 7.99,
                    "quantity_purchased": 1,
                    # No per-purchase supplier
                }
            ],
        })

        result = import_purchases(file_path)

        assert result.successful == 1

        with session_scope() as session:
            supplier = session.query(Supplier).filter_by(name="Header Supplier").first()
            assert supplier is not None
            purchase = session.query(Purchase).first()
            assert purchase.supplier_id == supplier.id

    def test_import_per_purchase_supplier_overrides_header(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        create_purchase_file,
    ):
        """Verify per-purchase supplier takes precedence over header."""
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "supplier": "Header Supplier",
            "purchases": [
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-12T14:15:23Z",
                    "unit_price": 7.99,
                    "quantity_purchased": 1,
                    "supplier": "Override Supplier",  # Per-purchase
                }
            ],
        })

        result = import_purchases(file_path)

        assert result.successful == 1

        with session_scope() as session:
            purchase = session.query(Purchase).first()
            supplier = session.query(Supplier).get(purchase.supplier_id)
            assert supplier.name == "Override Supplier"


# ============================================================================
# Test: File validation
# ============================================================================


class TestImportPurchasesFileValidation:
    """Test file validation and error handling."""

    def test_import_file_not_found(self, test_db, cleanup_transaction_data):
        """Verify proper error for missing file."""
        result = import_purchases("/nonexistent/path/file.json")

        assert result.failed == 1
        assert "File not found" in result.errors[0]["message"]

    def test_import_invalid_json(
        self, test_db, cleanup_transaction_data, create_purchase_file
    ):
        """Verify proper error for invalid JSON."""
        # Create file with invalid JSON manually
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            f.write("{ invalid json }")

        try:
            result = import_purchases(path)

            assert result.failed == 1
            assert "Invalid JSON" in result.errors[0]["message"]
        finally:
            os.remove(path)

    def test_import_wrong_import_type(
        self, test_db, cleanup_transaction_data, create_purchase_file
    ):
        """Verify proper error for wrong import_type."""
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "adjustments",  # Wrong type
            "purchases": [],
        })

        result = import_purchases(file_path)

        assert result.failed == 1
        assert "Invalid import_type" in result.errors[0]["message"]

    def test_import_empty_purchases_array(
        self, test_db, cleanup_transaction_data, create_purchase_file
    ):
        """Verify warning for empty purchases array."""
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "purchases": [],
        })

        result = import_purchases(file_path)

        assert result.successful == 0
        assert result.failed == 0
        assert len(result.warnings) == 1
        assert "No purchases" in result.warnings[0]["message"]


# ============================================================================
# Test: Helper functions
# ============================================================================


class TestHelperFunctions:
    """Test helper functions used by import_purchases."""

    def test_parse_datetime_iso_with_time(self):
        """Test parsing ISO datetime with time component."""
        result = _parse_datetime("2026-01-12T14:15:23Z")
        assert result == date(2026, 1, 12)

    def test_parse_datetime_simple_date(self):
        """Test parsing simple date format."""
        result = _parse_datetime("2026-01-12")
        assert result == date(2026, 1, 12)

    def test_parse_datetime_empty_string(self):
        """Test parsing empty string returns None."""
        result = _parse_datetime("")
        assert result is None

    def test_parse_datetime_none(self):
        """Test parsing None returns None."""
        result = _parse_datetime(None)
        assert result is None

    def test_parse_datetime_invalid(self):
        """Test parsing invalid string returns None."""
        result = _parse_datetime("not-a-date")
        assert result is None


# ============================================================================
# Test: Weighted average cost update
# ============================================================================


class TestImportPurchasesUpdatesAverageCost:
    """Test that average cost is recalculated after purchase import."""

    def test_import_updates_inventory_cost(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        create_purchase_file,
    ):
        """Verify InventoryItem has correct unit_cost from purchase."""
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "purchases": [
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-12T14:15:23Z",
                    "unit_price": 12.99,
                    "quantity_purchased": 3,
                }
            ],
        })

        result = import_purchases(file_path)

        assert result.successful == 1

        with session_scope() as session:
            inventory_item = session.query(InventoryItem).first()
            # unit_cost should match purchase unit_price
            assert inventory_item.unit_cost == 12.99

    def test_multiple_purchases_create_separate_inventory_items(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        create_purchase_file,
    ):
        """Verify each purchase creates its own InventoryItem with correct cost."""
        file_path = create_purchase_file({
            "schema_version": "4.0",
            "import_type": "purchases",
            "purchases": [
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-10T10:00:00Z",
                    "unit_price": 10.00,
                    "quantity_purchased": 2,
                },
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "purchased_at": "2026-01-11T11:00:00Z",
                    "unit_price": 12.00,
                    "quantity_purchased": 3,
                },
            ],
        })

        result = import_purchases(file_path)

        assert result.successful == 2

        with session_scope() as session:
            items = session.query(InventoryItem).order_by(
                InventoryItem.purchase_date
            ).all()
            assert len(items) == 2

            # First item: $10 x 2
            assert items[0].unit_cost == 10.00
            assert items[0].quantity == 2.0

            # Second item: $12 x 3
            assert items[1].unit_cost == 12.00
            assert items[1].quantity == 3.0

            # Total inventory: 2 + 3 = 5
            total_quantity = sum(i.quantity for i in items)
            assert total_quantity == 5.0

            # Weighted average should be: (10*2 + 12*3) / 5 = 56/5 = 11.2
            total_value = sum(i.unit_cost * i.quantity for i in items)
            assert total_value / total_quantity == 11.2


# ============================================================================
# Adjustment Import Tests (WP05)
# ============================================================================


@pytest.fixture
def sample_inventory_for_adjustment(test_db, sample_product_for_purchase):
    """Create sample inventory items for adjustment tests (FIFO testing)."""
    with session_scope() as session:
        # Create two inventory items with different dates for FIFO testing
        # Older item: 10 units from Jan 5
        older_item = InventoryItem(
            product_id=sample_product_for_purchase["id"],
            quantity=10.0,
            unit_cost=5.00,
            purchase_date=date(2026, 1, 5),
        )
        session.add(older_item)
        session.flush()
        older_id = older_item.id

        # Newer item: 15 units from Jan 10
        newer_item = InventoryItem(
            product_id=sample_product_for_purchase["id"],
            quantity=15.0,
            unit_cost=6.00,
            purchase_date=date(2026, 1, 10),
        )
        session.add(newer_item)
        session.flush()
        newer_id = newer_item.id

        return {
            "older_id": older_id,
            "older_quantity": 10.0,
            "older_cost": 5.00,
            "newer_id": newer_id,
            "newer_quantity": 15.0,
            "newer_cost": 6.00,
            "product_id": sample_product_for_purchase["id"],
            "product_slug": sample_product_for_purchase["slug"],
            "total_quantity": 25.0,
        }


@pytest.fixture
def create_adjustment_file():
    """Factory fixture to create temporary adjustment JSON files for testing."""
    created_files = []

    def _create_file(data: dict) -> str:
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        created_files.append(path)
        return path

    yield _create_file

    # Cleanup
    for path in created_files:
        if os.path.exists(path):
            os.remove(path)


# ============================================================================
# Test: import_adjustments decreases inventory
# ============================================================================


class TestImportAdjustmentsDecreasesInventory:
    """Test that import_adjustments correctly decreases inventory (SC-007)."""

    def test_import_adjustments_decreases_inventory(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_inventory_for_adjustment,
        create_adjustment_file,
    ):
        """Verify adjustment import decreases inventory quantities."""
        file_path = create_adjustment_file({
            "schema_version": "4.0",
            "import_type": "adjustments",
            "created_at": "2026-01-12T09:15:00Z",
            "source": "bt_mobile",
            "adjustments": [
                {
                    "product_slug": sample_inventory_for_adjustment["product_slug"],
                    "adjusted_at": "2026-01-12T09:10:12Z",
                    "quantity": -5.0,
                    "reason_code": "spoilage",
                    "notes": "Found mold, discarding",
                }
            ],
        })

        # Before adjustment: total = 25.0
        result = import_adjustments(file_path)

        assert result.successful == 1
        assert result.failed == 0

        # Verify inventory decreased
        with session_scope() as session:
            items = session.query(InventoryItem).filter(
                InventoryItem.product_id == sample_inventory_for_adjustment["product_id"]
            ).order_by(InventoryItem.purchase_date.asc()).all()

            total_quantity = sum(i.quantity for i in items)
            # 25 - 5 = 20
            assert total_quantity == 20.0


# ============================================================================
# Test: Positive quantity rejection (SC-008)
# ============================================================================


class TestImportAdjustmentsRejectsPositiveQuantity:
    """Test that positive adjustment attempts are rejected 100% (SC-008)."""

    def test_import_adjustments_rejects_positive_quantity(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_inventory_for_adjustment,
        create_adjustment_file,
    ):
        """Verify positive quantity is rejected with clear error."""
        file_path = create_adjustment_file({
            "schema_version": "4.0",
            "import_type": "adjustments",
            "adjustments": [
                {
                    "product_slug": sample_inventory_for_adjustment["product_slug"],
                    "adjusted_at": "2026-01-12T09:10:12Z",
                    "quantity": 5.0,  # POSITIVE - should be rejected
                    "reason_code": "spoilage",
                }
            ],
        })

        result = import_adjustments(file_path)

        assert result.successful == 0
        assert result.failed == 1
        assert len(result.errors) == 1
        assert "adjustments must be negative" in result.errors[0]["message"]
        assert "purchase import" in result.errors[0]["suggestion"]

    def test_import_adjustments_rejects_zero_quantity(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_inventory_for_adjustment,
        create_adjustment_file,
    ):
        """Verify zero quantity is rejected with clear error."""
        file_path = create_adjustment_file({
            "schema_version": "4.0",
            "import_type": "adjustments",
            "adjustments": [
                {
                    "product_slug": sample_inventory_for_adjustment["product_slug"],
                    "adjusted_at": "2026-01-12T09:10:12Z",
                    "quantity": 0,  # ZERO - should be rejected
                    "reason_code": "correction",
                }
            ],
        })

        result = import_adjustments(file_path)

        assert result.successful == 0
        assert result.failed == 1
        assert "adjustments must be negative" in result.errors[0]["message"]


# ============================================================================
# Test: reason_code validation
# ============================================================================


class TestImportAdjustmentsRequiresReasonCode:
    """Test that reason_code is required (FR-021)."""

    def test_import_adjustments_requires_reason_code(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_inventory_for_adjustment,
        create_adjustment_file,
    ):
        """Verify missing reason_code produces error."""
        file_path = create_adjustment_file({
            "schema_version": "4.0",
            "import_type": "adjustments",
            "adjustments": [
                {
                    "product_slug": sample_inventory_for_adjustment["product_slug"],
                    "adjusted_at": "2026-01-12T09:10:12Z",
                    "quantity": -5.0,
                    # No reason_code
                }
            ],
        })

        result = import_adjustments(file_path)

        assert result.successful == 0
        assert result.failed == 1
        assert "reason_code" in result.errors[0]["message"]
        # Suggestion should list valid codes
        assert "spoilage" in result.errors[0]["suggestion"] or "Valid codes" in result.errors[0]["suggestion"]

    def test_import_adjustments_rejects_invalid_reason_code(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_inventory_for_adjustment,
        create_adjustment_file,
    ):
        """Verify invalid reason_code is rejected."""
        file_path = create_adjustment_file({
            "schema_version": "4.0",
            "import_type": "adjustments",
            "adjustments": [
                {
                    "product_slug": sample_inventory_for_adjustment["product_slug"],
                    "adjusted_at": "2026-01-12T09:10:12Z",
                    "quantity": -5.0,
                    "reason_code": "invalid_reason",
                }
            ],
        })

        result = import_adjustments(file_path)

        assert result.successful == 0
        assert result.failed == 1
        assert "Invalid reason_code" in result.errors[0]["message"]
        assert "invalid_reason" in result.errors[0]["message"]

    def test_import_adjustments_accepts_valid_reason_codes(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_inventory_for_adjustment,
        create_adjustment_file,
    ):
        """Verify all valid reason codes are accepted."""
        for reason_code in ALLOWED_REASON_CODES:
            # Need to reset inventory for each test iteration
            with session_scope() as session:
                # Add back inventory if depleted
                items = session.query(InventoryItem).filter(
                    InventoryItem.product_id == sample_inventory_for_adjustment["product_id"]
                ).all()
                for item in items:
                    if item.quantity < 10:
                        item.quantity = 10.0

            file_path = create_adjustment_file({
                "schema_version": "4.0",
                "import_type": "adjustments",
                "adjustments": [
                    {
                        "product_slug": sample_inventory_for_adjustment["product_slug"],
                        "adjusted_at": "2026-01-12T09:10:12Z",
                        "quantity": -1.0,
                        "reason_code": reason_code,
                        "notes": f"Test {reason_code}" if reason_code == "other" else None,
                    }
                ],
            })

            result = import_adjustments(file_path)

            assert result.successful == 1, f"Failed for reason_code: {reason_code}"
            assert result.failed == 0, f"Failed for reason_code: {reason_code}"

    def test_import_adjustments_reason_code_case_insensitive(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_inventory_for_adjustment,
        create_adjustment_file,
    ):
        """Verify reason codes are matched case-insensitively (FR-021)."""
        # Test uppercase variants
        uppercase_codes = ["SPOILAGE", "DAMAGED", "WASTE", "CORRECTION", "OTHER"]

        for reason_code in uppercase_codes:
            # Reset inventory for each test iteration
            with session_scope() as session:
                items = session.query(InventoryItem).filter(
                    InventoryItem.product_id == sample_inventory_for_adjustment["product_id"]
                ).all()
                for item in items:
                    if item.quantity < 10:
                        item.quantity = 10.0

            file_path = create_adjustment_file({
                "schema_version": "4.0",
                "import_type": "adjustments",
                "adjustments": [
                    {
                        "product_slug": sample_inventory_for_adjustment["product_slug"],
                        "adjusted_at": "2026-01-12T09:10:12Z",
                        "quantity": -1.0,
                        "reason_code": reason_code,  # Uppercase
                    }
                ],
            })

            result = import_adjustments(file_path)

            assert result.successful == 1, f"Failed for uppercase reason_code: {reason_code}"
            assert result.failed == 0, f"Failed for uppercase reason_code: {reason_code}"


# ============================================================================
# Test: Prevent negative inventory (FR-022)
# ============================================================================


class TestImportAdjustmentsPreventsNegativeInventory:
    """Test that adjustments exceeding available inventory are rejected (FR-022)."""

    def test_import_adjustments_prevents_negative_inventory(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_inventory_for_adjustment,
        create_adjustment_file,
    ):
        """Verify adjustment exceeding available inventory is rejected."""
        # Total inventory is 25.0, try to adjust -30.0
        file_path = create_adjustment_file({
            "schema_version": "4.0",
            "import_type": "adjustments",
            "adjustments": [
                {
                    "product_slug": sample_inventory_for_adjustment["product_slug"],
                    "adjusted_at": "2026-01-12T09:10:12Z",
                    "quantity": -30.0,  # Exceeds available (25.0)
                    "reason_code": "waste",
                }
            ],
        })

        result = import_adjustments(file_path)

        assert result.successful == 0
        assert result.failed == 1
        assert "exceeds available inventory" in result.errors[0]["message"]
        assert "30" in result.errors[0]["message"]
        assert "25" in result.errors[0]["message"]

    def test_import_adjustments_allows_exact_inventory(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_inventory_for_adjustment,
        create_adjustment_file,
    ):
        """Verify adjustment exactly matching available inventory is allowed."""
        # Total inventory is 25.0, adjust exactly -25.0
        file_path = create_adjustment_file({
            "schema_version": "4.0",
            "import_type": "adjustments",
            "adjustments": [
                {
                    "product_slug": sample_inventory_for_adjustment["product_slug"],
                    "adjusted_at": "2026-01-12T09:10:12Z",
                    "quantity": -25.0,  # Exactly matches available
                    "reason_code": "correction",
                }
            ],
        })

        result = import_adjustments(file_path)

        assert result.successful == 1
        assert result.failed == 0

        # Verify inventory is now 0
        with session_scope() as session:
            items = session.query(InventoryItem).filter(
                InventoryItem.product_id == sample_inventory_for_adjustment["product_id"]
            ).all()
            total_quantity = sum(i.quantity for i in items)
            assert total_quantity == 0.0


# ============================================================================
# Test: FIFO ordering
# ============================================================================


class TestImportAdjustmentsUsesFIFO:
    """Test that adjustments use FIFO (oldest inventory first)."""

    def test_import_adjustments_uses_fifo(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_inventory_for_adjustment,
        create_adjustment_file,
    ):
        """Verify FIFO: adjustment reduces oldest inventory item first."""
        # Inventory: older=10.0 (Jan 5), newer=15.0 (Jan 10)
        # Adjust -8.0 should reduce older from 10 to 2
        file_path = create_adjustment_file({
            "schema_version": "4.0",
            "import_type": "adjustments",
            "adjustments": [
                {
                    "product_slug": sample_inventory_for_adjustment["product_slug"],
                    "adjusted_at": "2026-01-12T09:10:12Z",
                    "quantity": -8.0,
                    "reason_code": "spoilage",
                }
            ],
        })

        result = import_adjustments(file_path)

        assert result.successful == 1

        with session_scope() as session:
            items = session.query(InventoryItem).filter(
                InventoryItem.product_id == sample_inventory_for_adjustment["product_id"]
            ).order_by(InventoryItem.purchase_date.asc()).all()

            # Older item should be reduced from 10 to 2
            assert items[0].quantity == 2.0
            # Newer item should be unchanged at 15
            assert items[1].quantity == 15.0

    def test_import_adjustments_fifo_spans_items(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_inventory_for_adjustment,
        create_adjustment_file,
    ):
        """Verify FIFO spans multiple items when needed."""
        # Inventory: older=10.0 (Jan 5), newer=15.0 (Jan 10)
        # Adjust -12.0 should deplete older (10) and take 2 from newer
        file_path = create_adjustment_file({
            "schema_version": "4.0",
            "import_type": "adjustments",
            "adjustments": [
                {
                    "product_slug": sample_inventory_for_adjustment["product_slug"],
                    "adjusted_at": "2026-01-12T09:10:12Z",
                    "quantity": -12.0,
                    "reason_code": "waste",
                }
            ],
        })

        result = import_adjustments(file_path)

        assert result.successful == 1

        with session_scope() as session:
            items = session.query(InventoryItem).filter(
                InventoryItem.product_id == sample_inventory_for_adjustment["product_id"]
            ).order_by(InventoryItem.purchase_date.asc()).all()

            # Older item should be fully depleted (0)
            assert items[0].quantity == 0.0
            # Newer item should be reduced from 15 to 13
            assert items[1].quantity == 13.0


# ============================================================================
# Test: Depletion record creation
# ============================================================================


class TestImportAdjustmentsCreatesDepletionRecords:
    """Test that adjustment creates InventoryDepletion audit records."""

    def test_import_adjustments_creates_depletion_records(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_inventory_for_adjustment,
        create_adjustment_file,
    ):
        """Verify InventoryDepletion records are created for audit trail."""
        file_path = create_adjustment_file({
            "schema_version": "4.0",
            "import_type": "adjustments",
            "adjustments": [
                {
                    "product_slug": sample_inventory_for_adjustment["product_slug"],
                    "adjusted_at": "2026-01-12T09:10:12Z",
                    "quantity": -5.0,
                    "reason_code": "spoilage",
                    "notes": "Found mold",
                }
            ],
        })

        result = import_adjustments(file_path)

        assert result.successful == 1

        with session_scope() as session:
            depletions = session.query(InventoryDepletion).all()
            assert len(depletions) == 1

            depletion = depletions[0]
            assert float(depletion.quantity_depleted) == 5.0
            assert depletion.depletion_reason == "spoilage"
            assert depletion.notes == "Found mold"
            assert depletion.created_by == "import:adjustment"

    def test_import_adjustments_creates_multiple_depletion_records_for_fifo(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_inventory_for_adjustment,
        create_adjustment_file,
    ):
        """Verify multiple depletion records when FIFO spans items."""
        # Adjust -12.0 spans two items
        file_path = create_adjustment_file({
            "schema_version": "4.0",
            "import_type": "adjustments",
            "adjustments": [
                {
                    "product_slug": sample_inventory_for_adjustment["product_slug"],
                    "adjusted_at": "2026-01-12T09:10:12Z",
                    "quantity": -12.0,
                    "reason_code": "waste",
                    "notes": "Burned batch",
                }
            ],
        })

        result = import_adjustments(file_path)

        assert result.successful == 1

        with session_scope() as session:
            depletions = session.query(InventoryDepletion).order_by(
                InventoryDepletion.id
            ).all()

            # Should have 2 depletion records (one per inventory item)
            assert len(depletions) == 2

            # First depletion: 10.0 from older item
            assert float(depletions[0].quantity_depleted) == 10.0
            assert depletions[0].inventory_item_id == sample_inventory_for_adjustment["older_id"]

            # Second depletion: 2.0 from newer item
            assert float(depletions[1].quantity_depleted) == 2.0
            assert depletions[1].inventory_item_id == sample_inventory_for_adjustment["newer_id"]

    def test_depletion_cost_calculated_correctly(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_inventory_for_adjustment,
        create_adjustment_file,
    ):
        """Verify depletion cost is calculated from unit_cost."""
        file_path = create_adjustment_file({
            "schema_version": "4.0",
            "import_type": "adjustments",
            "adjustments": [
                {
                    "product_slug": sample_inventory_for_adjustment["product_slug"],
                    "adjusted_at": "2026-01-12T09:10:12Z",
                    "quantity": -5.0,
                    "reason_code": "spoilage",
                }
            ],
        })

        result = import_adjustments(file_path)

        assert result.successful == 1

        with session_scope() as session:
            depletion = session.query(InventoryDepletion).first()
            # Older item has unit_cost of 5.00, depleting 5 units = 25.00 cost
            assert float(depletion.cost) == 25.0


# ============================================================================
# Test: Dry run mode
# ============================================================================


class TestImportAdjustmentsDryRun:
    """Test dry_run mode validates without committing."""

    def test_dry_run_no_commit(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_inventory_for_adjustment,
        create_adjustment_file,
    ):
        """Verify dry_run=True does not modify database."""
        file_path = create_adjustment_file({
            "schema_version": "4.0",
            "import_type": "adjustments",
            "adjustments": [
                {
                    "product_slug": sample_inventory_for_adjustment["product_slug"],
                    "adjusted_at": "2026-01-12T09:10:12Z",
                    "quantity": -5.0,
                    "reason_code": "spoilage",
                }
            ],
        })

        result = import_adjustments(file_path, dry_run=True)

        # Should report success from validation perspective
        assert result.successful == 1
        assert result.failed == 0

        # But inventory should be unchanged
        with session_scope() as session:
            items = session.query(InventoryItem).filter(
                InventoryItem.product_id == sample_inventory_for_adjustment["product_id"]
            ).all()
            total_quantity = sum(i.quantity for i in items)
            assert total_quantity == 25.0  # Unchanged

            # No depletion records
            depletions = session.query(InventoryDepletion).all()
            assert len(depletions) == 0


# ============================================================================
# Test: File and schema validation
# ============================================================================


class TestImportAdjustmentsFileValidation:
    """Test file validation and error handling."""

    def test_import_rejects_wrong_import_type(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_inventory_for_adjustment,
        create_adjustment_file,
    ):
        """Verify wrong import_type is rejected."""
        file_path = create_adjustment_file({
            "schema_version": "4.0",
            "import_type": "purchases",  # Wrong type
            "adjustments": [
                {
                    "product_slug": sample_inventory_for_adjustment["product_slug"],
                    "quantity": -5.0,
                    "reason_code": "spoilage",
                }
            ],
        })

        result = import_adjustments(file_path)

        assert result.failed == 1
        assert "Invalid import_type" in result.errors[0]["message"]

    def test_import_accepts_inventory_updates_type(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,
        sample_inventory_for_adjustment,
        create_adjustment_file,
    ):
        """Verify 'inventory_updates' import_type is accepted."""
        file_path = create_adjustment_file({
            "schema_version": "4.0",
            "import_type": "inventory_updates",  # Alternative valid type
            "inventory_updates": [  # Alternative key name
                {
                    "product_slug": sample_inventory_for_adjustment["product_slug"],
                    "adjusted_at": "2026-01-12T09:10:12Z",
                    "quantity": -5.0,
                    "reason_code": "correction",
                }
            ],
        })

        result = import_adjustments(file_path)

        assert result.successful == 1
        assert result.failed == 0

    def test_import_rejects_unknown_product(
        self,
        test_db,
        cleanup_transaction_data,
        create_adjustment_file,
    ):
        """Verify unknown product_slug produces error."""
        file_path = create_adjustment_file({
            "schema_version": "4.0",
            "import_type": "adjustments",
            "adjustments": [
                {
                    "product_slug": "nonexistent_product",
                    "quantity": -5.0,
                    "reason_code": "spoilage",
                }
            ],
        })

        result = import_adjustments(file_path)

        assert result.failed == 1
        assert "not found" in result.errors[0]["message"]

    def test_import_rejects_product_with_no_inventory(
        self,
        test_db,
        cleanup_transaction_data,
        sample_product_for_purchase,  # Product exists but no inventory
        create_adjustment_file,
    ):
        """Verify product with no inventory produces error."""
        file_path = create_adjustment_file({
            "schema_version": "4.0",
            "import_type": "adjustments",
            "adjustments": [
                {
                    "product_slug": sample_product_for_purchase["slug"],
                    "quantity": -5.0,
                    "reason_code": "spoilage",
                }
            ],
        })

        result = import_adjustments(file_path)

        assert result.failed == 1
        assert "No inventory found" in result.errors[0]["message"]
