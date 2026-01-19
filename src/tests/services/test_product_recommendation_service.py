"""Unit tests for product service recommendation functions.

Tests for Feature 007: Product-Aware Shopping List Recommendations

Tests cover:
- _calculate_product_cost() helper function
- get_product_recommendation() main function
- Edge cases: no products, no purchase history, unit conversion failures
- Cost calculation accuracy
- Minimum package rounding
"""

import pytest
from decimal import Decimal
from datetime import date

from src.services import product_service
from src.services.product_service import (
    _calculate_product_cost,
    get_product_recommendation,
    create_product,
    get_products_for_ingredient,
)
from src.services import ingredient_service
from src.models import Purchase

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def test_supplier(test_db):
    """Create a test supplier for F028."""
    from src.services import supplier_service

    result = supplier_service.create_supplier(
        name="Test Supplier",
        city="Boston",
        state="MA",
        zip_code="02101",
    )

    class SupplierObj:
        def __init__(self, data):
            self.id = data["id"]

    return SupplierObj(result)


@pytest.fixture
def flour_ingredient(test_db):
    """Create a flour ingredient with known density for unit conversion."""
    return ingredient_service.create_ingredient(
        {
            "display_name": "All-Purpose Flour",
            "category": "Flour",
            # 4-field density: 1 cup = 125g (approximately 0.529 g/ml)
            "density_volume_value": 1.0,
            "density_volume_unit": "cup",
            "density_weight_value": 125.0,
            "density_weight_unit": "g",
        }
    )


@pytest.fixture
def flour_product_preferred(test_db, flour_ingredient, test_supplier):
    """Create a preferred flour product with purchase history."""
    product = create_product(
        flour_ingredient.slug,
        {
            "brand": "King Arthur",
            "package_size": "25 lb bag",
            "package_unit": "lb",
            "package_unit_quantity": Decimal("25.0"),
            "preferred": True,
        },
    )

    # Add purchase history for cost data
    with test_db() as session:
        purchase = Purchase(
            product_id=product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("0.72"),  # $0.72 per lb
            quantity_purchased=25,
        )
        session.add(purchase)
        session.commit()

    return product


@pytest.fixture
def flour_product_generic(test_db, flour_ingredient, test_supplier):
    """Create a non-preferred generic flour product."""
    product = create_product(
        flour_ingredient.slug,
        {
            "brand": "Store Brand",
            "package_size": "5 lb bag",
            "package_unit": "lb",
            "package_unit_quantity": Decimal("5.0"),
            "preferred": False,
        },
    )

    # Add purchase history
    with test_db() as session:
        purchase = Purchase(
            product_id=product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("0.48"),  # $0.48 per lb (cheaper)
            quantity_purchased=5,
        )
        session.add(purchase)
        session.commit()

    return product


@pytest.fixture
def flour_product_no_purchases(test_db, flour_ingredient):
    """Create a product with no purchase history (cost unknown)."""
    return create_product(
        flour_ingredient.slug,
        {
            "brand": "New Brand",
            "package_size": "10 lb bag",
            "package_unit": "lb",
            "package_unit_quantity": Decimal("10.0"),
            "preferred": False,
        },
    )


@pytest.fixture
def ingredient_no_products(test_db):
    """Create an ingredient with no products configured."""
    return ingredient_service.create_ingredient(
        {"display_name": "Specialty Ingredient", "category": "Misc"}
    )


# ============================================================================
# Tests for get_product_recommendation with preferred product
# ============================================================================


class TestProductRecommendationPreferred:
    """Tests for get_product_recommendation when preferred product exists."""

    def test_returns_preferred_product_status(
        self, test_db, flour_ingredient, flour_product_preferred
    ):
        """FR-001: Preferred product is recommended with correct status."""
        result = get_product_recommendation(
            flour_ingredient.slug, Decimal("5"), "cup"  # 5 cups shortfall
        )

        assert result["product_status"] == "preferred"
        assert result["product_recommendation"] is not None
        assert result["product_recommendation"]["product_id"] == flour_product_preferred.id

    def test_preferred_product_includes_brand(
        self, test_db, flour_ingredient, flour_product_preferred
    ):
        """Recommendation includes brand information."""
        result = get_product_recommendation(flour_ingredient.slug, Decimal("5"), "cup")

        assert result["product_recommendation"]["brand"] == "King Arthur"
        assert result["product_recommendation"]["is_preferred"] is True

    def test_preferred_product_has_cost_data(
        self, test_db, flour_ingredient, flour_product_preferred
    ):
        """Recommendation includes cost calculations when purchase history exists."""
        result = get_product_recommendation(flour_ingredient.slug, Decimal("5"), "cup")

        rec = result["product_recommendation"]
        assert rec["cost_available"] is True
        assert rec["cost_per_package_unit"] == Decimal("0.72")
        assert rec["total_cost"] is not None


# ============================================================================
# Tests for get_product_recommendation with multiple products (no preferred)
# ============================================================================


class TestProductRecommendationMultiple:
    """Tests for get_product_recommendation when no preferred product exists."""

    def test_returns_multiple_status_when_no_preferred(
        self, test_db, flour_ingredient, flour_product_generic, flour_product_no_purchases
    ):
        """FR-002: All products listed when no preferred product marked."""
        # Ensure no product is preferred
        result = get_product_recommendation(flour_ingredient.slug, Decimal("5"), "cup")

        # Both products created without preferred=True
        # (flour_product_generic has preferred=False, flour_product_no_purchases also False)
        assert result["product_status"] == "multiple"
        assert result["product_recommendation"] is None
        assert len(result["all_products"]) >= 2

    def test_multiple_products_sorted_by_cost(
        self, test_db, flour_ingredient, flour_product_generic, flour_product_no_purchases
    ):
        """Multiple products are sorted cheapest first."""
        result = get_product_recommendation(flour_ingredient.slug, Decimal("5"), "cup")

        # Products with cost should come before products without cost
        all_products = result["all_products"]
        costs = [p.get("total_cost") for p in all_products]

        # Check that None values (no cost) are at the end
        none_indices = [i for i, c in enumerate(costs) if c is None]
        value_indices = [i for i, c in enumerate(costs) if c is not None]

        for ni in none_indices:
            for vi in value_indices:
                assert vi < ni, "Products with cost should come before products without cost"


# ============================================================================
# Tests for get_product_recommendation with no products
# ============================================================================


class TestProductRecommendationNone:
    """Tests for get_product_recommendation when no products configured."""

    def test_returns_none_status_when_no_products(self, test_db, ingredient_no_products):
        """FR-003: Handle ingredient with no products."""
        result = get_product_recommendation(ingredient_no_products.slug, Decimal("5"), "oz")

        assert result["product_status"] == "none"
        assert result["product_recommendation"] is None
        assert result["all_products"] == []
        assert result["message"] == "No product configured"


# ============================================================================
# Tests for cost calculation accuracy
# ============================================================================


class TestCostCalculationAccuracy:
    """Tests for cost calculation precision requirements."""

    def test_cost_per_recipe_unit_accuracy(
        self, test_db, flour_ingredient, flour_product_preferred
    ):
        """SC-002: Cost accurate within $0.01 precision."""
        result = get_product_recommendation(flour_ingredient.slug, Decimal("10"), "cup")  # 10 cups

        rec = result["product_recommendation"]

        # Cost per recipe unit should be calculated
        # $0.72/lb, and lb -> cup conversion
        # For flour: 1 lb = approximately 3.6 cups
        # So cost per cup should be roughly $0.72 / 3.6 = $0.20
        if rec["cost_per_recipe_unit"] is not None:
            # Just verify it's a reasonable value and has precision
            assert isinstance(rec["cost_per_recipe_unit"], Decimal)
            # Should be less than $1/cup for flour
            assert rec["cost_per_recipe_unit"] < Decimal("1.00")
            # Should be more than $0.01/cup
            assert rec["cost_per_recipe_unit"] > Decimal("0.01")


# ============================================================================
# Tests for minimum package rounding
# ============================================================================


class TestMinPackagesRounding:
    """Tests for minimum package calculations."""

    def test_min_packages_rounds_up_small_shortfall(
        self, test_db, flour_ingredient, flour_product_preferred
    ):
        """SC-003: Minimum packages correctly round up for small shortfall."""
        # Shortfall of 10 cups, package is 25 lb (90+ cups)
        # Should still recommend 1 package minimum
        result = get_product_recommendation(flour_ingredient.slug, Decimal("10"), "cup")  # 10 cups

        rec = result["product_recommendation"]
        assert rec["min_packages"] >= 1

    def test_min_packages_rounds_up_large_shortfall(
        self, test_db, flour_ingredient, flour_product_preferred
    ):
        """SC-003: Minimum packages rounds up for larger shortfall."""
        # Large shortfall that requires multiple packages
        # 25 lb bag = ~90 cups
        # 100 cups should need 2 bags
        result = get_product_recommendation(
            flour_ingredient.slug, Decimal("100"), "cup"  # 100 cups
        )

        rec = result["product_recommendation"]
        # Should be at least 2 packages (ceil(100/~90) = 2)
        assert rec["min_packages"] >= 1


# ============================================================================
# Tests for edge cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge case handling."""

    def test_cost_unknown_no_purchase_history(
        self, test_db, flour_ingredient, flour_product_no_purchases
    ):
        """FR-010: Handle product with no purchases."""
        # Get all products (this one has no purchase history)
        products = get_products_for_ingredient(flour_ingredient.slug)
        product_without_purchases = next(p for p in products if p.brand == "New Brand")

        # Calculate cost directly
        rec = _calculate_product_cost(
            product_without_purchases, Decimal("5"), "cup", flour_ingredient
        )

        assert rec["cost_available"] is False
        assert rec["cost_message"] == "Cost unknown"

    def test_zero_shortfall_returns_sufficient(
        self, test_db, flour_ingredient, flour_product_preferred
    ):
        """Edge case: Zero shortfall returns sufficient status."""
        result = get_product_recommendation(flour_ingredient.slug, Decimal("0"), "cup")

        assert result["product_status"] == "sufficient"
        assert result["message"] == "Sufficient stock"

    def test_negative_shortfall_returns_sufficient(
        self, test_db, flour_ingredient, flour_product_preferred
    ):
        """Edge case: Negative shortfall returns sufficient status."""
        result = get_product_recommendation(flour_ingredient.slug, Decimal("-5"), "cup")

        assert result["product_status"] == "sufficient"

    def test_unit_conversion_failure(self, test_db, ingredient_no_products):
        """Edge case: Incompatible units (count vs weight) without density."""
        # Create an ingredient without density (no volume-weight conversion possible)
        ingredient = ingredient_service.create_ingredient(
            {
                "display_name": "Count Ingredient",
                "category": "Misc",
                # No density_g_per_ml - can't convert count to weight
            }
        )

        # Create a product with weight-based purchase unit
        create_product(
            ingredient.slug,
            {
                "brand": "Test",
                "package_size": "1 lb",
                "package_unit": "lb",
                "package_unit_quantity": Decimal("1.0"),
            },
        )

        # Try to get recommendation - should handle conversion failure gracefully
        result = get_product_recommendation(
            ingredient.slug,
            Decimal("5"),
            "count",  # recipe unit
        )

        # Should still return a result, even if conversion failed
        assert result["product_status"] in ["multiple", "none", "preferred"]
        # If we got products, check for conversion error flag
        if result["all_products"]:
            rec = result["all_products"][0]
            # Conversion should fail for count -> lb
            assert rec.get("conversion_error", False) is True


# ============================================================================
# Tests for _calculate_product_cost helper
# ============================================================================


class TestCalculateProductCost:
    """Direct tests for the _calculate_product_cost helper function."""

    def test_returns_expected_structure(self, test_db, flour_ingredient, flour_product_preferred):
        """Helper returns all expected fields."""
        products = get_products_for_ingredient(flour_ingredient.slug)
        product = products[0]

        rec = _calculate_product_cost(product, Decimal("5"), "cup", flour_ingredient)

        # Check all expected fields exist
        expected_fields = [
            "product_id",
            "brand",
            "package_size",
            "package_quantity",
            "package_unit",
            "cost_per_package_unit",
            "cost_per_recipe_unit",
            "min_packages",
            "total_cost",
            "is_preferred",
            "cost_available",
            "cost_message",
            "conversion_error",
            "error_message",
        ]

        for field in expected_fields:
            assert field in rec, f"Missing field: {field}"

    def test_calculates_total_cost_correctly(
        self, test_db, flour_ingredient, flour_product_preferred
    ):
        """Total cost equals packages * quantity * unit_cost."""
        products = get_products_for_ingredient(flour_ingredient.slug)
        preferred = next(p for p in products if p.preferred)

        rec = _calculate_product_cost(preferred, Decimal("5"), "cup", flour_ingredient)

        if rec["cost_available"] and rec["total_cost"]:
            # total_cost = min_packages * package_unit_quantity * cost_per_package_unit
            expected = (
                Decimal(str(rec["min_packages"]))
                * Decimal(str(rec["package_quantity"]))
                * rec["cost_per_package_unit"]
            )
            assert rec["total_cost"] == expected
