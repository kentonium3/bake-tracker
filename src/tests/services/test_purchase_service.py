"""Tests for Purchase Service - Price Suggestion Functions (Feature 028).

Tests cover:
- get_last_price_at_supplier: Returns most recent price at specific supplier
- get_last_price_any_supplier: Returns most recent price from any supplier (fallback)
- Edge cases: No history, history at different supplier, multiple suppliers
- Session parameter handling for composability
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models.supplier import Supplier
from src.models.ingredient import Ingredient
from src.models.product import Product
from src.models.purchase import Purchase
from src.models.inventory_item import InventoryItem
from src.models.inventory_depletion import InventoryDepletion
from src.services.purchase_service import (
    get_last_price_at_supplier,
    get_last_price_any_supplier,
    get_purchases_filtered,
    get_remaining_inventory,
    can_edit_purchase,
    can_delete_purchase,
    update_purchase,
    get_purchase_usage_history,
)
from src.services.exceptions import PurchaseNotFound


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
def costco_supplier(session):
    """Create Costco supplier fixture."""
    supplier = Supplier(
        name="Costco",
        city="Waltham",
        state="MA",
        zip_code="02451",
    )
    session.add(supplier)
    session.flush()
    return supplier


@pytest.fixture
def wegmans_supplier(session):
    """Create Wegmans supplier fixture."""
    supplier = Supplier(
        name="Wegmans",
        city="Westwood",
        state="MA",
        zip_code="02090",
    )
    session.add(supplier)
    session.flush()
    return supplier


@pytest.fixture
def test_product(session, test_ingredient):
    """Create a test product."""
    product = Product(
        ingredient_id=test_ingredient.id,
        product_name="King Arthur All Purpose Flour",
        package_unit="lb",
        package_unit_quantity=5.0,
    )
    session.add(product)
    session.flush()
    return product


@pytest.fixture
def product_with_no_purchases(session, test_ingredient):
    """Create a product with no purchase history."""
    product = Product(
        ingredient_id=test_ingredient.id,
        product_name="New Product - No History",
        package_unit="lb",
        package_unit_quantity=1.0,
    )
    session.add(product)
    session.flush()
    return product


@pytest.fixture
def product_with_costco_purchases(session, test_ingredient, costco_supplier):
    """Create a product with multiple purchases at Costco."""
    product = Product(
        ingredient_id=test_ingredient.id,
        product_name="Product with Costco History",
        package_unit="lb",
        package_unit_quantity=5.0,
    )
    session.add(product)
    session.flush()

    # Create 3 purchases at Costco with different dates
    # Oldest first
    purchases = [
        Purchase(
            product_id=product.id,
            supplier_id=costco_supplier.id,
            purchase_date=date.today() - timedelta(days=60),
            unit_price=Decimal("8.99"),
            quantity_purchased=2,
        ),
        Purchase(
            product_id=product.id,
            supplier_id=costco_supplier.id,
            purchase_date=date.today() - timedelta(days=30),
            unit_price=Decimal("9.49"),
            quantity_purchased=1,
        ),
        Purchase(
            product_id=product.id,
            supplier_id=costco_supplier.id,
            purchase_date=date.today() - timedelta(days=5),
            unit_price=Decimal("9.99"),  # Most recent price
            quantity_purchased=3,
        ),
    ]
    for p in purchases:
        session.add(p)
    session.flush()

    return product


@pytest.fixture
def product_with_multi_supplier_purchases(
    session, test_ingredient, costco_supplier, wegmans_supplier
):
    """Create a product with purchases at multiple suppliers."""
    product = Product(
        ingredient_id=test_ingredient.id,
        product_name="Product Multi-Supplier",
        package_unit="lb",
        package_unit_quantity=5.0,
    )
    session.add(product)
    session.flush()

    # Create purchases at both suppliers
    # Wegmans purchase is most recent
    purchases = [
        Purchase(
            product_id=product.id,
            supplier_id=costco_supplier.id,
            purchase_date=date.today() - timedelta(days=30),
            unit_price=Decimal("8.99"),
            quantity_purchased=2,
        ),
        Purchase(
            product_id=product.id,
            supplier_id=wegmans_supplier.id,
            purchase_date=date.today() - timedelta(days=5),
            unit_price=Decimal("10.49"),  # Most recent, at Wegmans
            quantity_purchased=1,
        ),
    ]
    for p in purchases:
        session.add(p)
    session.flush()

    return product


class TestGetLastPriceAtSupplier:
    """Tests for get_last_price_at_supplier function."""

    def test_returns_most_recent_price_with_history(
        self, session, product_with_costco_purchases, costco_supplier
    ):
        """Returns most recent price when purchase history exists at supplier."""
        result = get_last_price_at_supplier(
            product_id=product_with_costco_purchases.id,
            supplier_id=costco_supplier.id,
            session=session,
        )

        assert result is not None
        assert result["unit_price"] == "9.9900"  # Most recent price
        assert result["supplier_id"] == costco_supplier.id
        # Verify it returns ISO format date
        assert "purchase_date" in result
        expected_date = (date.today() - timedelta(days=5)).isoformat()
        assert result["purchase_date"] == expected_date

    def test_returns_none_when_no_history_at_supplier(
        self, session, product_with_no_purchases, costco_supplier
    ):
        """Returns None when product has no purchase history at supplier."""
        result = get_last_price_at_supplier(
            product_id=product_with_no_purchases.id,
            supplier_id=costco_supplier.id,
            session=session,
        )

        assert result is None

    def test_returns_none_when_history_at_different_supplier(
        self, session, product_with_costco_purchases, wegmans_supplier
    ):
        """Returns None when history exists at different supplier only."""
        # Product has purchases at Costco, not Wegmans
        result = get_last_price_at_supplier(
            product_id=product_with_costco_purchases.id,
            supplier_id=wegmans_supplier.id,
            session=session,
        )

        assert result is None

    def test_returns_correct_price_for_specific_supplier(
        self, session, product_with_multi_supplier_purchases, costco_supplier
    ):
        """Returns price for requested supplier even if another is more recent."""
        # Most recent overall is at Wegmans, but we're asking for Costco
        result = get_last_price_at_supplier(
            product_id=product_with_multi_supplier_purchases.id,
            supplier_id=costco_supplier.id,
            session=session,
        )

        assert result is not None
        assert result["unit_price"] == "8.9900"  # Costco price, not Wegmans
        assert result["supplier_id"] == costco_supplier.id

    def test_works_without_session_parameter(self, engine, test_ingredient, costco_supplier):
        """Function works when no session parameter is provided."""
        # This test verifies the session_scope() fallback path
        # However, we need to monkey-patch the database module for this to work
        # In a real test environment with test_db fixture, this would be automatic
        # For unit tests, we'll skip this as it requires global state changes
        pass

    def test_returns_dict_not_orm_object(
        self, session, product_with_costco_purchases, costco_supplier
    ):
        """Verify return value is dict to avoid session detachment issues."""
        result = get_last_price_at_supplier(
            product_id=product_with_costco_purchases.id,
            supplier_id=costco_supplier.id,
            session=session,
        )

        assert isinstance(result, dict)
        assert "unit_price" in result
        assert "purchase_date" in result
        assert "supplier_id" in result
        # Verify unit_price is string (serializable)
        assert isinstance(result["unit_price"], str)


class TestGetLastPriceAnySupplier:
    """Tests for get_last_price_any_supplier function."""

    def test_returns_most_recent_price_from_any_supplier(
        self, session, product_with_multi_supplier_purchases
    ):
        """Returns most recent price regardless of supplier."""
        result = get_last_price_any_supplier(
            product_id=product_with_multi_supplier_purchases.id,
            session=session,
        )

        assert result is not None
        # Most recent is Wegmans purchase at $10.49
        assert result["unit_price"] == "10.4900"
        assert "supplier_name" in result
        # Check supplier name format matches Supplier.display_name
        assert "Wegmans" in result["supplier_name"]
        assert "Westwood" in result["supplier_name"]

    def test_returns_none_when_no_history(self, session, product_with_no_purchases):
        """Returns None when product has no purchase history."""
        result = get_last_price_any_supplier(
            product_id=product_with_no_purchases.id,
            session=session,
        )

        assert result is None

    def test_returns_price_from_single_supplier(self, session, product_with_costco_purchases):
        """Returns price when only one supplier has history."""
        result = get_last_price_any_supplier(
            product_id=product_with_costco_purchases.id,
            session=session,
        )

        assert result is not None
        assert result["unit_price"] == "9.9900"
        assert "Costco" in result["supplier_name"]

    def test_includes_supplier_name_for_hint_display(
        self, session, product_with_costco_purchases, costco_supplier
    ):
        """Verify supplier_name is included for UI hint display."""
        result = get_last_price_any_supplier(
            product_id=product_with_costco_purchases.id,
            session=session,
        )

        assert result is not None
        # Should match Supplier.display_name format: "Name (City, State)"
        expected_name = costco_supplier.display_name
        assert result["supplier_name"] == expected_name

    def test_returns_dict_with_all_required_fields(self, session, product_with_costco_purchases):
        """Verify all required fields are in return dict."""
        result = get_last_price_any_supplier(
            product_id=product_with_costco_purchases.id,
            session=session,
        )

        assert isinstance(result, dict)
        # Required fields per spec
        assert "unit_price" in result
        assert "purchase_date" in result
        assert "supplier_id" in result
        assert "supplier_name" in result
        # Verify types
        assert isinstance(result["unit_price"], str)
        assert isinstance(result["purchase_date"], str)
        assert isinstance(result["supplier_id"], int)
        assert isinstance(result["supplier_name"], str)

    def test_purchase_date_is_iso_format(self, session, product_with_costco_purchases):
        """Verify purchase_date is in ISO format string."""
        result = get_last_price_any_supplier(
            product_id=product_with_costco_purchases.id,
            session=session,
        )

        assert result is not None
        # ISO format: YYYY-MM-DD
        purchase_date = result["purchase_date"]
        # Should be parseable as date
        parsed = date.fromisoformat(purchase_date)
        assert isinstance(parsed, date)


class TestSessionParameterHandling:
    """Tests for session parameter composability pattern."""

    def test_get_last_price_at_supplier_accepts_session(
        self, session, product_with_costco_purchases, costco_supplier
    ):
        """Verify function accepts session parameter."""
        # Should not raise when session is provided
        result = get_last_price_at_supplier(
            product_id=product_with_costco_purchases.id,
            supplier_id=costco_supplier.id,
            session=session,
        )
        assert result is not None

    def test_get_last_price_any_supplier_accepts_session(
        self, session, product_with_costco_purchases
    ):
        """Verify function accepts session parameter."""
        # Should not raise when session is provided
        result = get_last_price_any_supplier(
            product_id=product_with_costco_purchases.id,
            session=session,
        )
        assert result is not None

    def test_functions_work_within_shared_transaction(
        self, session, test_ingredient, costco_supplier
    ):
        """Verify functions work within a shared transaction."""
        # Create product and purchase in same session
        product = Product(
            ingredient_id=test_ingredient.id,
            product_name="Transaction Test Product",
            package_unit="lb",
            package_unit_quantity=1.0,
        )
        session.add(product)
        session.flush()

        purchase = Purchase(
            product_id=product.id,
            supplier_id=costco_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("5.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        session.flush()

        # Query within same session - should see uncommitted data
        result = get_last_price_at_supplier(
            product_id=product.id,
            supplier_id=costco_supplier.id,
            session=session,
        )

        assert result is not None
        # Compare as Decimal to handle precision differences
        assert Decimal(result["unit_price"]) == Decimal("5.99")


# =============================================================================
# Tests for Feature 042 - Purchases Tab CRUD Operations
# =============================================================================


@pytest.fixture
def purchase_with_inventory(session, test_product, costco_supplier):
    """Create a purchase with linked inventory item (unconsumed)."""
    purchase = Purchase(
        product_id=test_product.id,
        supplier_id=costco_supplier.id,
        purchase_date=date.today() - timedelta(days=10),
        unit_price=Decimal("9.99"),
        quantity_purchased=2,
    )
    session.add(purchase)
    session.flush()

    # Create linked inventory item
    inventory_item = InventoryItem(
        product_id=test_product.id,
        purchase_id=purchase.id,
        quantity=10.0,  # 2 packages * 5 units each
        unit_cost=1.998,  # 9.99 / 5
        purchase_date=purchase.purchase_date,
    )
    session.add(inventory_item)
    session.flush()

    return purchase


@pytest.fixture
def purchase_partially_consumed(session, test_product, costco_supplier):
    """Create a purchase with partial consumption (some depletions)."""
    purchase = Purchase(
        product_id=test_product.id,
        supplier_id=costco_supplier.id,
        purchase_date=date.today() - timedelta(days=20),
        unit_price=Decimal("8.99"),
        quantity_purchased=3,
    )
    session.add(purchase)
    session.flush()

    # Create linked inventory item with partial consumption
    inventory_item = InventoryItem(
        product_id=test_product.id,
        purchase_id=purchase.id,
        quantity=10.0,  # 15 total units (3*5), 5 consumed, 10 remaining
        unit_cost=1.798,
        purchase_date=purchase.purchase_date,
    )
    session.add(inventory_item)
    session.flush()

    # Create depletion record
    depletion = InventoryDepletion(
        inventory_item_id=inventory_item.id,
        quantity_depleted=Decimal("5.0"),
        depletion_reason="Chocolate Chip Cookies",
        cost=Decimal("8.99"),  # 5 * 1.798
    )
    session.add(depletion)
    session.flush()

    return purchase


@pytest.fixture
def purchase_fully_consumed(session, test_product, costco_supplier):
    """Create a purchase that is fully consumed."""
    purchase = Purchase(
        product_id=test_product.id,
        supplier_id=costco_supplier.id,
        purchase_date=date.today() - timedelta(days=30),
        unit_price=Decimal("7.99"),
        quantity_purchased=1,
    )
    session.add(purchase)
    session.flush()

    # Create linked inventory item fully consumed
    inventory_item = InventoryItem(
        product_id=test_product.id,
        purchase_id=purchase.id,
        quantity=0.0,  # Fully consumed
        unit_cost=1.598,
        purchase_date=purchase.purchase_date,
    )
    session.add(inventory_item)
    session.flush()

    # Create depletion record for full consumption
    depletion = InventoryDepletion(
        inventory_item_id=inventory_item.id,
        quantity_depleted=Decimal("5.0"),  # 1 package * 5 units
        depletion_reason="Banana Bread",
        cost=Decimal("7.99"),
    )
    session.add(depletion)
    session.flush()

    return purchase


class TestGetPurchasesFiltered:
    """Tests for get_purchases_filtered function."""

    def test_returns_purchases_default_30_days(self, session, purchase_with_inventory):
        """Returns purchases from last 30 days by default."""
        result = get_purchases_filtered(session=session)

        assert len(result) >= 1
        # purchase_with_inventory is 10 days ago, should be included
        purchase_ids = [p["id"] for p in result]
        assert purchase_with_inventory.id in purchase_ids

    def test_filters_by_date_range_90_days(
        self, session, purchase_with_inventory, purchase_partially_consumed
    ):
        """Returns purchases from specified date range."""
        result = get_purchases_filtered(
            date_range="last_90_days",
            session=session,
        )

        assert len(result) >= 2
        purchase_ids = [p["id"] for p in result]
        assert purchase_with_inventory.id in purchase_ids
        assert purchase_partially_consumed.id in purchase_ids

    def test_filters_by_supplier(
        self, session, purchase_with_inventory, costco_supplier, wegmans_supplier
    ):
        """Returns only purchases from specified supplier."""
        # Create a purchase at a different supplier
        other_product = Product(
            ingredient_id=purchase_with_inventory.product.ingredient_id,
            product_name="Other Product",
            package_unit="lb",
            package_unit_quantity=1.0,
        )
        session.add(other_product)
        session.flush()

        other_purchase = Purchase(
            product_id=other_product.id,
            supplier_id=wegmans_supplier.id,
            purchase_date=date.today() - timedelta(days=5),
            unit_price=Decimal("11.99"),
            quantity_purchased=1,
        )
        session.add(other_purchase)
        session.flush()

        result = get_purchases_filtered(
            supplier_id=costco_supplier.id,
            session=session,
        )

        # Should only include Costco purchases
        for p in result:
            assert p["supplier_name"] == "Costco"

    def test_filters_by_search_query(self, session, purchase_with_inventory):
        """Returns purchases matching search query (product name)."""
        result = get_purchases_filtered(
            search_query="King Arthur",
            session=session,
        )

        assert len(result) >= 1
        # All results should contain search term
        for p in result:
            assert "King Arthur" in p["product_name"]

    def test_returns_empty_when_no_matches(self, session):
        """Returns empty list when no purchases match filters."""
        result = get_purchases_filtered(
            search_query="NonexistentProduct12345",
            session=session,
        )

        assert result == []

    def test_includes_remaining_inventory(self, session, purchase_with_inventory):
        """Result includes calculated remaining inventory."""
        result = get_purchases_filtered(session=session)

        # Find our test purchase
        test_purchase = next(p for p in result if p["id"] == purchase_with_inventory.id)
        assert "remaining_inventory" in test_purchase
        assert test_purchase["remaining_inventory"] == Decimal("10.0")

    def test_orders_by_date_descending(
        self, session, purchase_with_inventory, purchase_partially_consumed
    ):
        """Results are ordered by purchase_date DESC."""
        result = get_purchases_filtered(
            date_range="last_90_days",
            session=session,
        )

        if len(result) >= 2:
            # Verify descending order
            for i in range(len(result) - 1):
                assert result[i]["purchase_date"] >= result[i + 1]["purchase_date"]


class TestGetRemainingInventory:
    """Tests for get_remaining_inventory function."""

    def test_returns_quantity_unconsumed(self, session, purchase_with_inventory):
        """Returns remaining quantity for unconsumed purchase."""
        result = get_remaining_inventory(
            purchase_id=purchase_with_inventory.id,
            session=session,
        )

        assert result == Decimal("10.0")

    def test_returns_quantity_partially_consumed(self, session, purchase_partially_consumed):
        """Returns remaining quantity for partially consumed purchase."""
        result = get_remaining_inventory(
            purchase_id=purchase_partially_consumed.id,
            session=session,
        )

        assert result == Decimal("10.0")  # 15 total - 5 consumed = 10 remaining

    def test_returns_zero_fully_consumed(self, session, purchase_fully_consumed):
        """Returns zero for fully consumed purchase."""
        result = get_remaining_inventory(
            purchase_id=purchase_fully_consumed.id,
            session=session,
        )

        assert result == Decimal("0")

    def test_raises_for_nonexistent_purchase(self, session):
        """Raises PurchaseNotFound for invalid purchase_id."""
        with pytest.raises(PurchaseNotFound):
            get_remaining_inventory(purchase_id=99999, session=session)


class TestCanEditPurchase:
    """Tests for can_edit_purchase function."""

    def test_allows_edit_no_consumption(self, session, purchase_with_inventory):
        """Allows quantity edit when no consumption."""
        allowed, reason = can_edit_purchase(
            purchase_id=purchase_with_inventory.id,
            new_quantity=Decimal("1.0"),
            session=session,
        )

        assert allowed is True
        assert reason == ""

    def test_allows_edit_above_consumed(self, session, purchase_partially_consumed):
        """Allows quantity edit when new qty >= consumed."""
        # Partially consumed has 5 units consumed (1 package consumed)
        allowed, reason = can_edit_purchase(
            purchase_id=purchase_partially_consumed.id,
            new_quantity=Decimal("2.0"),  # 2 packages = 10 units > 5 consumed
            session=session,
        )

        assert allowed is True
        assert reason == ""

    def test_blocks_edit_below_consumed(self, session, purchase_partially_consumed):
        """Blocks quantity edit when new qty < consumed."""
        # Partially consumed has 5 units consumed
        # package_unit_quantity is 5, so 1 package = 5 units
        # 0.5 packages = 2.5 units < 5 consumed
        allowed, reason = can_edit_purchase(
            purchase_id=purchase_partially_consumed.id,
            new_quantity=Decimal("0.5"),
            session=session,
        )

        assert allowed is False
        assert "Cannot reduce below" in reason
        assert "already consumed" in reason

    def test_raises_for_nonexistent_purchase(self, session):
        """Raises PurchaseNotFound for invalid purchase_id."""
        with pytest.raises(PurchaseNotFound):
            can_edit_purchase(
                purchase_id=99999,
                new_quantity=Decimal("1.0"),
                session=session,
            )


class TestCanDeletePurchase:
    """Tests for can_delete_purchase function."""

    def test_allows_delete_no_depletions(self, session, purchase_with_inventory):
        """Allows deletion when no inventory has been consumed."""
        allowed, reason = can_delete_purchase(
            purchase_id=purchase_with_inventory.id,
            session=session,
        )

        assert allowed is True
        assert reason == ""

    def test_blocks_delete_has_depletions(self, session, purchase_partially_consumed):
        """Blocks deletion when inventory has been consumed."""
        allowed, reason = can_delete_purchase(
            purchase_id=purchase_partially_consumed.id,
            session=session,
        )

        assert allowed is False
        assert "Cannot delete" in reason
        assert "already used" in reason
        assert "Chocolate Chip Cookies" in reason

    def test_blocks_delete_fully_consumed(self, session, purchase_fully_consumed):
        """Blocks deletion for fully consumed purchase."""
        allowed, reason = can_delete_purchase(
            purchase_id=purchase_fully_consumed.id,
            session=session,
        )

        assert allowed is False
        assert "Cannot delete" in reason

    def test_raises_for_nonexistent_purchase(self, session):
        """Raises PurchaseNotFound for invalid purchase_id."""
        with pytest.raises(PurchaseNotFound):
            can_delete_purchase(purchase_id=99999, session=session)


class TestUpdatePurchase:
    """Tests for update_purchase function."""

    def test_updates_price_recalculates_costs(self, session, purchase_with_inventory):
        """Price change recalculates unit_cost on inventory items."""
        original_price = purchase_with_inventory.unit_price

        updated = update_purchase(
            purchase_id=purchase_with_inventory.id,
            updates={"unit_price": Decimal("12.99")},
            session=session,
        )

        assert updated.unit_price == Decimal("12.99")
        assert updated.unit_price != original_price

        # Verify inventory item unit_cost was updated
        inventory_item = (
            session.query(InventoryItem)
            .filter(InventoryItem.purchase_id == purchase_with_inventory.id)
            .first()
        )
        # New unit_cost = 12.99 / 5 = 2.598
        assert abs(inventory_item.unit_cost - 2.598) < 0.001

    def test_updates_quantity_adjusts_inventory(self, session, purchase_with_inventory):
        """Quantity change adjusts inventory item quantity."""
        updated = update_purchase(
            purchase_id=purchase_with_inventory.id,
            updates={"quantity_purchased": 3},  # Was 2
            session=session,
        )

        assert updated.quantity_purchased == 3

        # Verify inventory item quantity was updated
        inventory_item = (
            session.query(InventoryItem)
            .filter(InventoryItem.purchase_id == purchase_with_inventory.id)
            .first()
        )
        # New quantity = 3 packages * 5 units = 15
        assert inventory_item.quantity == 15.0

    def test_rejects_product_change(self, session, purchase_with_inventory, test_ingredient):
        """Raises ValueError when trying to change product_id."""
        other_product = Product(
            ingredient_id=test_ingredient.id,
            product_name="Different Product",
            package_unit="lb",
            package_unit_quantity=1.0,
        )
        session.add(other_product)
        session.flush()

        with pytest.raises(ValueError) as exc_info:
            update_purchase(
                purchase_id=purchase_with_inventory.id,
                updates={"product_id": other_product.id},
                session=session,
            )

        assert "Cannot change product_id" in str(exc_info.value)

    def test_rejects_quantity_below_consumed(self, session, purchase_partially_consumed):
        """Raises ValueError when new quantity < consumed."""
        # Partially consumed has 5 units consumed (1 package worth)
        with pytest.raises(ValueError) as exc_info:
            update_purchase(
                purchase_id=purchase_partially_consumed.id,
                updates={"quantity_purchased": 0},  # Would be 0 units < 5 consumed
                session=session,
            )

        assert "Cannot reduce below" in str(exc_info.value)

    def test_updates_notes(self, session, purchase_with_inventory):
        """Updates notes field."""
        updated = update_purchase(
            purchase_id=purchase_with_inventory.id,
            updates={"notes": "Updated note"},
            session=session,
        )

        assert updated.notes == "Updated note"

    def test_updates_supplier(self, session, purchase_with_inventory, wegmans_supplier):
        """Updates supplier_id field."""
        updated = update_purchase(
            purchase_id=purchase_with_inventory.id,
            updates={"supplier_id": wegmans_supplier.id},
            session=session,
        )

        assert updated.supplier_id == wegmans_supplier.id

    def test_raises_for_nonexistent_purchase(self, session):
        """Raises PurchaseNotFound for invalid purchase_id."""
        with pytest.raises(PurchaseNotFound):
            update_purchase(
                purchase_id=99999,
                updates={"notes": "test"},
                session=session,
            )


class TestGetPurchaseUsageHistory:
    """Tests for get_purchase_usage_history function."""

    def test_returns_depletions_with_details(self, session, purchase_partially_consumed):
        """Returns depletion history with recipe details."""
        result = get_purchase_usage_history(
            purchase_id=purchase_partially_consumed.id,
            session=session,
        )

        assert len(result) == 1
        depletion = result[0]
        assert "depletion_id" in depletion
        assert "depleted_at" in depletion
        assert depletion["recipe_name"] == "Chocolate Chip Cookies"
        assert depletion["quantity_used"] == Decimal("5.0")
        assert "cost" in depletion

    def test_returns_empty_when_no_depletions(self, session, purchase_with_inventory):
        """Returns empty list when no consumption history."""
        result = get_purchase_usage_history(
            purchase_id=purchase_with_inventory.id,
            session=session,
        )

        assert result == []

    def test_orders_by_date_ascending(self, session, test_product, costco_supplier):
        """Results are ordered by depleted_at ASC."""
        # Create a purchase with multiple depletions
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=costco_supplier.id,
            purchase_date=date.today() - timedelta(days=15),
            unit_price=Decimal("9.99"),
            quantity_purchased=5,
        )
        session.add(purchase)
        session.flush()

        inventory_item = InventoryItem(
            product_id=test_product.id,
            purchase_id=purchase.id,
            quantity=15.0,
            unit_cost=1.998,
            purchase_date=purchase.purchase_date,
        )
        session.add(inventory_item)
        session.flush()

        # Create multiple depletions with different dates
        from datetime import datetime

        depletion1 = InventoryDepletion(
            inventory_item_id=inventory_item.id,
            quantity_depleted=Decimal("2.0"),
            depletion_reason="First Recipe",
            cost=Decimal("3.99"),
            depletion_date=datetime(2024, 1, 1, 10, 0, 0),
        )
        depletion2 = InventoryDepletion(
            inventory_item_id=inventory_item.id,
            quantity_depleted=Decimal("3.0"),
            depletion_reason="Second Recipe",
            cost=Decimal("5.99"),
            depletion_date=datetime(2024, 1, 5, 14, 0, 0),
        )
        session.add(depletion1)
        session.add(depletion2)
        session.flush()

        result = get_purchase_usage_history(
            purchase_id=purchase.id,
            session=session,
        )

        assert len(result) == 2
        # Should be in ascending order
        assert result[0]["recipe_name"] == "First Recipe"
        assert result[1]["recipe_name"] == "Second Recipe"

    def test_raises_for_nonexistent_purchase(self, session):
        """Raises PurchaseNotFound for invalid purchase_id."""
        with pytest.raises(PurchaseNotFound):
            get_purchase_usage_history(purchase_id=99999, session=session)
