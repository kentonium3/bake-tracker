"""Integration tests for purchase recording and price analysis workflow.

Tests purchase history tracking, price trend detection, and alerts.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from src.services import ingredient_service, product_service, purchase_service

def test_purchase_and_price_analysis(test_db):
    """Test: Record purchases -> Calculate averages -> Detect price changes."""

    # Setup: Create ingredient and product
    ingredient = ingredient_service.create_ingredient(
        {"name": "Whole Wheat Flour", "category": "Flour"}
    )

    product = product_service.create_product(
        ingredient.slug,
        {
            "brand": "Bob's Red Mill",
            "package_size": "5 lb bag",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("5.0")
        }
    )

    # 1. Record historical purchases over 90 days
    base_date = date.today() - timedelta(days=90)
    purchases = []

    for i in range(6):
        purchase = purchase_service.record_purchase(
            product_id=product.id,
            quantity=Decimal("5.0"),
            total_cost=Decimal(f"{3.50 + i * 0.10:.2f}"),  # $3.50, $3.60, $3.70, ...
            purchase_date=base_date + timedelta(days=i * 15),
            store="Whole Foods"
        )
        purchases.append(purchase)

    assert len(purchases) == 6

    # Verify unit cost auto-calculation
    assert purchases[0].unit_cost == Decimal("0.70")  # $3.50 / 5 lb
    assert purchases[-1].unit_cost == Decimal("0.80")  # $4.00 / 5 lb

    # 2. Calculate average price (60-day window)
    avg_price = purchase_service.calculate_average_price(product.id, days=60)
    assert avg_price is not None
    assert Decimal("0.70") <= avg_price <= Decimal("0.80")

    # 3. Record new purchase with significant price increase
    new_purchase = purchase_service.record_purchase(
        product_id=product.id,
        quantity=Decimal("5.0"),
        total_cost=Decimal("5.25"),  # $1.05/lb (~35% increase)
        purchase_date=date.today(),
        store="Whole Foods"
    )

    assert new_purchase.unit_cost == Decimal("1.05")

    # 4. Detect price change alert
    alert = purchase_service.detect_price_change(
        product_id=product.id, new_unit_cost=Decimal("1.05"), comparison_days=60
    )

    assert alert is not None
    assert alert["alert_level"] == "warning"  # 20-40% increase
    assert alert["change_percent"] > Decimal("20.0")
    assert "increased" in alert["message"].lower()

    # 5. Get price trend (linear regression)
    trend = purchase_service.get_price_trend(product.id, days=90)

    assert trend["direction"] == "increasing"
    assert trend["data_points"] == 7  # 6 historical + 1 new
    assert trend["slope_per_day"] > Decimal("0.0")

def test_purchase_history_filtering(test_db):
    """Test: Record multiple purchases -> Filter by date range and store."""

    # Setup
    ingredient = ingredient_service.create_ingredient(
        {"name": "Brown Sugar", "category": "Sugar"}
    )

    product = product_service.create_product(
        ingredient.slug,
        {
            "brand": "C&H",
            "package_size": "2 lb bag",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("2.0")
        }
    )

    # Record purchases at different stores and dates
    purchase1 = purchase_service.record_purchase(
        product_id=product.id,
        quantity=Decimal("2.0"),
        total_cost=Decimal("3.99"),
        purchase_date=date(2025, 1, 1),
        store="Costco"
    )

    purchase2 = purchase_service.record_purchase(
        product_id=product.id,
        quantity=Decimal("2.0"),
        total_cost=Decimal("4.49"),
        purchase_date=date(2025, 1, 15),
        store="Safeway"
    )

    purchase3 = purchase_service.record_purchase(
        product_id=product.id,
        quantity=Decimal("2.0"),
        total_cost=Decimal("3.89"),
        purchase_date=date(2025, 2, 1),
        store="Costco"
    )

    # Filter by date range
    january_purchases = purchase_service.get_purchase_history(
        product_id=product.id, start_date=date(2025, 1, 1), end_date=date(2025, 1, 31)
    )
    assert len(january_purchases) == 2

    # Filter by store
    costco_purchases = purchase_service.get_purchase_history(product_id=product.id, store="Costco")
    assert len(costco_purchases) == 2

    # Verify sorting (most recent first)
    all_purchases = purchase_service.get_purchase_history(product_id=product.id)
    assert all_purchases[0].purchase_date >= all_purchases[1].purchase_date
    assert all_purchases[1].purchase_date >= all_purchases[2].purchase_date

def test_price_trend_insufficient_data(test_db):
    """Test: Price trend with < 2 data points returns stable."""

    # Setup
    ingredient = ingredient_service.create_ingredient(
        {"name": "Vanilla Extract", "category": "Extracts"}
    )

    product = product_service.create_product(
        ingredient.slug,
        {
            "brand": "Nielsen-Massey",
            "package_size": "4 oz bottle",
            "purchase_unit": "oz",
            "purchase_quantity": Decimal("4.0")
        }
    )

    # Single purchase
    purchase_service.record_purchase(
        product_id=product.id,
        quantity=Decimal("4.0"),
        total_cost=Decimal("12.99"),
        purchase_date=date.today()
    )

    # Get trend with insufficient data
    trend = purchase_service.get_price_trend(product.id, days=90)

    assert trend["direction"] == "stable"
    assert trend["data_points"] == 1
    assert trend["slope_per_day"] == Decimal("0.0")
    assert "Insufficient data" in trend["message"]

def test_most_recent_purchase(test_db):
    """Test: Multiple purchases -> Get most recent."""

    # Setup
    ingredient = ingredient_service.create_ingredient(
        {"name": "Honey", "category": "Syrups"}
    )

    product = product_service.create_product(
        ingredient.slug,
        {
            "brand": "Local Beekeeper",
            "package_size": "16 oz jar",
            "purchase_unit": "oz",
            "purchase_quantity": Decimal("16.0")
        }
    )

    # Record purchases
    purchase1 = purchase_service.record_purchase(
        product_id=product.id,
        quantity=Decimal("16.0"),
        total_cost=Decimal("8.99"),
        purchase_date=date.today() - timedelta(days=60)
    )

    purchase2 = purchase_service.record_purchase(
        product_id=product.id,
        quantity=Decimal("16.0"),
        total_cost=Decimal("9.49"),
        purchase_date=date.today() - timedelta(days=30)
    )

    purchase3 = purchase_service.record_purchase(
        product_id=product.id,
        quantity=Decimal("16.0"),
        total_cost=Decimal("9.99"),
        purchase_date=date.today()
    )

    # Get most recent
    recent = purchase_service.get_most_recent_purchase(product.id)

    assert recent.id == purchase3.id
    assert recent.purchase_date == date.today()
    assert abs(recent.total_cost - 9.99) < 0.01  # Compare as float with tolerance

def test_no_purchase_history_returns_none(test_db):
    """Test: Product with no purchases returns None for averages."""

    # Setup
    ingredient = ingredient_service.create_ingredient(
        {"name": "Cinnamon", "category": "Spices"}
    )

    product = product_service.create_product(
        ingredient.slug,
        {
            "brand": "McCormick",
            "package_size": "2.37 oz bottle",
            "purchase_unit": "oz",
            "purchase_quantity": Decimal("2.37")
        }
    )

    # No purchases yet
    avg_price = purchase_service.calculate_average_price(product.id, days=60)
    assert avg_price is None

    most_recent = purchase_service.get_most_recent_purchase(product.id)
    assert most_recent is None
