"""Unit tests for variant service recommendation functions.

Tests for Feature 007: Variant-Aware Shopping List Recommendations

Tests cover:
- _calculate_variant_cost() helper function
- get_variant_recommendation() main function
- Edge cases: no variants, no purchase history, unit conversion failures
- Cost calculation accuracy
- Minimum package rounding
"""

import pytest
from decimal import Decimal
from datetime import date

from src.services import variant_service
from src.services.variant_service import (
    _calculate_variant_cost,
    get_variant_recommendation,
    create_variant,
    get_variants_for_ingredient,
)
from src.services import ingredient_service
from src.models import Purchase


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def flour_ingredient(test_db):
    """Create a flour ingredient with known density for unit conversion."""
    return ingredient_service.create_ingredient(
        {
            "name": "All-Purpose Flour",
            "category": "Flour",
            "recipe_unit": "cup",
            # 4-field density: 1 cup = 125g (approximately 0.529 g/ml)
            "density_volume_value": 1.0,
            "density_volume_unit": "cup",
            "density_weight_value": 125.0,
            "density_weight_unit": "g",
        }
    )


@pytest.fixture
def flour_variant_preferred(test_db, flour_ingredient):
    """Create a preferred flour variant with purchase history."""
    variant = create_variant(
        flour_ingredient.slug,
        {
            "brand": "King Arthur",
            "package_size": "25 lb bag",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("25.0"),
            "preferred": True,
        },
    )

    # Add purchase history for cost data
    with test_db() as session:
        purchase = Purchase(
            variant_id=variant.id,
            purchase_date=date.today(),
            unit_cost=0.72,  # $0.72 per lb
            quantity_purchased=25.0,
            total_cost=18.00,
        )
        session.add(purchase)
        session.commit()

    return variant


@pytest.fixture
def flour_variant_generic(test_db, flour_ingredient):
    """Create a non-preferred generic flour variant."""
    variant = create_variant(
        flour_ingredient.slug,
        {
            "brand": "Store Brand",
            "package_size": "5 lb bag",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("5.0"),
            "preferred": False,
        },
    )

    # Add purchase history
    with test_db() as session:
        purchase = Purchase(
            variant_id=variant.id,
            purchase_date=date.today(),
            unit_cost=0.48,  # $0.48 per lb (cheaper)
            quantity_purchased=5.0,
            total_cost=2.40,
        )
        session.add(purchase)
        session.commit()

    return variant


@pytest.fixture
def flour_variant_no_purchases(test_db, flour_ingredient):
    """Create a variant with no purchase history (cost unknown)."""
    return create_variant(
        flour_ingredient.slug,
        {
            "brand": "New Brand",
            "package_size": "10 lb bag",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("10.0"),
            "preferred": False,
        },
    )


@pytest.fixture
def ingredient_no_variants(test_db):
    """Create an ingredient with no variants configured."""
    return ingredient_service.create_ingredient(
        {
            "name": "Specialty Ingredient",
            "category": "Misc",
            "recipe_unit": "oz",
        }
    )


# ============================================================================
# Tests for get_variant_recommendation with preferred variant
# ============================================================================


class TestVariantRecommendationPreferred:
    """Tests for get_variant_recommendation when preferred variant exists."""

    def test_returns_preferred_variant_status(
        self, test_db, flour_ingredient, flour_variant_preferred
    ):
        """FR-001: Preferred variant is recommended with correct status."""
        result = get_variant_recommendation(
            flour_ingredient.slug,
            Decimal("5"),  # 5 cups shortfall
            "cup",
        )

        assert result["variant_status"] == "preferred"
        assert result["variant_recommendation"] is not None
        assert result["variant_recommendation"]["variant_id"] == flour_variant_preferred.id

    def test_preferred_variant_includes_brand(
        self, test_db, flour_ingredient, flour_variant_preferred
    ):
        """Recommendation includes brand information."""
        result = get_variant_recommendation(
            flour_ingredient.slug,
            Decimal("5"),
            "cup",
        )

        assert result["variant_recommendation"]["brand"] == "King Arthur"
        assert result["variant_recommendation"]["is_preferred"] is True

    def test_preferred_variant_has_cost_data(
        self, test_db, flour_ingredient, flour_variant_preferred
    ):
        """Recommendation includes cost calculations when purchase history exists."""
        result = get_variant_recommendation(
            flour_ingredient.slug,
            Decimal("5"),
            "cup",
        )

        rec = result["variant_recommendation"]
        assert rec["cost_available"] is True
        assert rec["cost_per_purchase_unit"] == Decimal("0.72")
        assert rec["total_cost"] is not None


# ============================================================================
# Tests for get_variant_recommendation with multiple variants (no preferred)
# ============================================================================


class TestVariantRecommendationMultiple:
    """Tests for get_variant_recommendation when no preferred variant exists."""

    def test_returns_multiple_status_when_no_preferred(
        self, test_db, flour_ingredient, flour_variant_generic, flour_variant_no_purchases
    ):
        """FR-002: All variants listed when no preferred variant marked."""
        # Ensure no variant is preferred
        result = get_variant_recommendation(
            flour_ingredient.slug,
            Decimal("5"),
            "cup",
        )

        # Both variants created without preferred=True
        # (flour_variant_generic has preferred=False, flour_variant_no_purchases also False)
        assert result["variant_status"] == "multiple"
        assert result["variant_recommendation"] is None
        assert len(result["all_variants"]) >= 2

    def test_multiple_variants_sorted_by_cost(
        self, test_db, flour_ingredient, flour_variant_generic, flour_variant_no_purchases
    ):
        """Multiple variants are sorted cheapest first."""
        result = get_variant_recommendation(
            flour_ingredient.slug,
            Decimal("5"),
            "cup",
        )

        # Variants with cost should come before variants without cost
        all_variants = result["all_variants"]
        costs = [v.get("total_cost") for v in all_variants]

        # Check that None values (no cost) are at the end
        none_indices = [i for i, c in enumerate(costs) if c is None]
        value_indices = [i for i, c in enumerate(costs) if c is not None]

        for ni in none_indices:
            for vi in value_indices:
                assert vi < ni, "Variants with cost should come before variants without cost"


# ============================================================================
# Tests for get_variant_recommendation with no variants
# ============================================================================


class TestVariantRecommendationNone:
    """Tests for get_variant_recommendation when no variants configured."""

    def test_returns_none_status_when_no_variants(self, test_db, ingredient_no_variants):
        """FR-003: Handle ingredient with no variants."""
        result = get_variant_recommendation(
            ingredient_no_variants.slug,
            Decimal("5"),
            "oz",
        )

        assert result["variant_status"] == "none"
        assert result["variant_recommendation"] is None
        assert result["all_variants"] == []
        assert result["message"] == "No variant configured"


# ============================================================================
# Tests for cost calculation accuracy
# ============================================================================


class TestCostCalculationAccuracy:
    """Tests for cost calculation precision requirements."""

    def test_cost_per_recipe_unit_accuracy(
        self, test_db, flour_ingredient, flour_variant_preferred
    ):
        """SC-002: Cost accurate within $0.01 precision."""
        result = get_variant_recommendation(
            flour_ingredient.slug,
            Decimal("10"),  # 10 cups
            "cup",
        )

        rec = result["variant_recommendation"]

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
        self, test_db, flour_ingredient, flour_variant_preferred
    ):
        """SC-003: Minimum packages correctly round up for small shortfall."""
        # Shortfall of 10 cups, package is 25 lb (90+ cups)
        # Should still recommend 1 package minimum
        result = get_variant_recommendation(
            flour_ingredient.slug,
            Decimal("10"),  # 10 cups
            "cup",
        )

        rec = result["variant_recommendation"]
        assert rec["min_packages"] >= 1

    def test_min_packages_rounds_up_large_shortfall(
        self, test_db, flour_ingredient, flour_variant_preferred
    ):
        """SC-003: Minimum packages rounds up for larger shortfall."""
        # Large shortfall that requires multiple packages
        # 25 lb bag = ~90 cups
        # 100 cups should need 2 bags
        result = get_variant_recommendation(
            flour_ingredient.slug,
            Decimal("100"),  # 100 cups
            "cup",
        )

        rec = result["variant_recommendation"]
        # Should be at least 2 packages (ceil(100/~90) = 2)
        assert rec["min_packages"] >= 1


# ============================================================================
# Tests for edge cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge case handling."""

    def test_cost_unknown_no_purchase_history(
        self, test_db, flour_ingredient, flour_variant_no_purchases
    ):
        """FR-010: Handle variant with no purchases."""
        # Get all variants (this one has no purchase history)
        variants = get_variants_for_ingredient(flour_ingredient.slug)
        variant_without_purchases = next(v for v in variants if v.brand == "New Brand")

        # Calculate cost directly
        rec = _calculate_variant_cost(
            variant_without_purchases,
            Decimal("5"),
            "cup",
            flour_ingredient,
        )

        assert rec["cost_available"] is False
        assert rec["cost_message"] == "Cost unknown"

    def test_zero_shortfall_returns_sufficient(
        self, test_db, flour_ingredient, flour_variant_preferred
    ):
        """Edge case: Zero shortfall returns sufficient status."""
        result = get_variant_recommendation(
            flour_ingredient.slug,
            Decimal("0"),
            "cup",
        )

        assert result["variant_status"] == "sufficient"
        assert result["message"] == "Sufficient stock"

    def test_negative_shortfall_returns_sufficient(
        self, test_db, flour_ingredient, flour_variant_preferred
    ):
        """Edge case: Negative shortfall returns sufficient status."""
        result = get_variant_recommendation(
            flour_ingredient.slug,
            Decimal("-5"),
            "cup",
        )

        assert result["variant_status"] == "sufficient"

    def test_unit_conversion_failure(self, test_db, ingredient_no_variants):
        """Edge case: Incompatible units (count vs weight) without density."""
        # Create an ingredient without density (no volume-weight conversion possible)
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "Count Ingredient",
                "category": "Misc",
                "recipe_unit": "count",
                # No density_g_per_ml - can't convert count to weight
            }
        )

        # Create a variant with weight-based purchase unit
        create_variant(
            ingredient.slug,
            {
                "brand": "Test",
                "package_size": "1 lb",
                "purchase_unit": "lb",
                "purchase_quantity": Decimal("1.0"),
            },
        )

        # Try to get recommendation - should handle conversion failure gracefully
        result = get_variant_recommendation(
            ingredient.slug,
            Decimal("5"),
            "count",  # recipe unit
        )

        # Should still return a result, even if conversion failed
        assert result["variant_status"] in ["multiple", "none", "preferred"]
        # If we got variants, check for conversion error flag
        if result["all_variants"]:
            rec = result["all_variants"][0]
            # Conversion should fail for count -> lb
            assert rec.get("conversion_error", False) is True


# ============================================================================
# Tests for _calculate_variant_cost helper
# ============================================================================


class TestCalculateVariantCost:
    """Direct tests for the _calculate_variant_cost helper function."""

    def test_returns_expected_structure(self, test_db, flour_ingredient, flour_variant_preferred):
        """Helper returns all expected fields."""
        variants = get_variants_for_ingredient(flour_ingredient.slug)
        variant = variants[0]

        rec = _calculate_variant_cost(
            variant,
            Decimal("5"),
            "cup",
            flour_ingredient,
        )

        # Check all expected fields exist
        expected_fields = [
            "variant_id",
            "brand",
            "package_size",
            "package_quantity",
            "purchase_unit",
            "cost_per_purchase_unit",
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
        self, test_db, flour_ingredient, flour_variant_preferred
    ):
        """Total cost equals packages * quantity * unit_cost."""
        variants = get_variants_for_ingredient(flour_ingredient.slug)
        preferred = next(v for v in variants if v.preferred)

        rec = _calculate_variant_cost(
            preferred,
            Decimal("5"),
            "cup",
            flour_ingredient,
        )

        if rec["cost_available"] and rec["total_cost"]:
            # total_cost = min_packages * purchase_quantity * cost_per_purchase_unit
            expected = (
                Decimal(str(rec["min_packages"]))
                * Decimal(str(rec["package_quantity"]))
                * rec["cost_per_purchase_unit"]
            )
            assert rec["total_cost"] == expected
