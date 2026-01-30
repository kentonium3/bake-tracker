"""
Tests for migration transformation script.

Feature 084: MaterialUnit Schema Refactor
WP09: Migration Transformation Script
"""

import pytest
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from migrate_material_units import (
    transform_export_data,
    transform_material_units,
    transform_compositions,
    build_products_by_material_lookup,
    get_unique_slug,
    MigrationLog,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_materials():
    return [
        {"slug": "red-ribbon", "name": "Red Ribbon"},
        {"slug": "clear-bags", "name": "Clear Bags"},
    ]


@pytest.fixture
def sample_products():
    return [
        {"slug": "michaels-red-25m", "material_slug": "red-ribbon"},
        {"slug": "joann-red-50m", "material_slug": "red-ribbon"},
        {"slug": "amazon-bags-100", "material_slug": "clear-bags"},
    ]


@pytest.fixture
def sample_units_old_format():
    return [
        {
            "material_slug": "red-ribbon",
            "name": "6-inch cut",
            "slug": "6-inch-cut",
            "quantity_per_unit": 0.1524,
        },
        {
            "material_slug": "clear-bags",
            "name": "1 bag",
            "slug": "1-bag",
            "quantity_per_unit": 1.0,
        },
    ]


# ============================================================================
# Build Products Lookup Tests
# ============================================================================


class TestBuildProductsLookup:
    def test_groups_products_by_material(self, sample_products):
        lookup = build_products_by_material_lookup(sample_products)

        assert "red-ribbon" in lookup
        assert len(lookup["red-ribbon"]) == 2
        assert "clear-bags" in lookup
        assert len(lookup["clear-bags"]) == 1

    def test_empty_products_returns_empty_lookup(self):
        lookup = build_products_by_material_lookup([])
        assert lookup == {}

    def test_products_without_material_slug_ignored(self):
        products = [
            {"slug": "prod1"},  # No material_slug
            {"slug": "prod2", "material_slug": ""},  # Empty material_slug
            {"slug": "prod3", "material_slug": "test"},  # Valid
        ]
        lookup = build_products_by_material_lookup(products)
        assert "test" in lookup
        assert len(lookup) == 1


# ============================================================================
# Unique Slug Tests
# ============================================================================


class TestGetUniqueSlug:
    def test_returns_original_if_unique(self):
        existing = {"other-slug"}
        result = get_unique_slug("test-slug", existing)
        assert result == "test-slug"

    def test_adds_suffix_if_collision(self):
        existing = {"test-slug"}
        result = get_unique_slug("test-slug", existing)
        assert result == "test-slug-2"

    def test_increments_suffix_for_multiple_collisions(self):
        existing = {"test-slug", "test-slug-2", "test-slug-3"}
        result = get_unique_slug("test-slug", existing)
        assert result == "test-slug-4"


# ============================================================================
# Transform MaterialUnits Tests
# ============================================================================


class TestTransformMaterialUnits:
    def test_duplicates_units_across_products(
        self, sample_materials, sample_products, sample_units_old_format
    ):
        materials = {m["slug"]: m for m in sample_materials}
        products_by_material = build_products_by_material_lookup(sample_products)
        log = MigrationLog()

        result, orphaned = transform_material_units(
            sample_units_old_format, materials, products_by_material, log
        )

        # Red ribbon unit should be duplicated to 2 products
        red_units = [u for u in result if "red" in u["material_product_slug"]]
        assert len(red_units) == 2

        # Clear bags unit should map to 1 product
        bag_units = [u for u in result if "bags" in u["material_product_slug"]]
        assert len(bag_units) == 1

        # Total: 2 + 1 = 3
        assert len(result) == 3
        assert log.material_units_created == 3
        assert len(orphaned) == 0

    def test_orphaned_units_not_in_output(self, sample_materials):
        materials = {m["slug"]: m for m in sample_materials}
        products_by_material = {}  # No products
        log = MigrationLog()

        units = [{"material_slug": "red-ribbon", "name": "Test", "slug": "test"}]
        result, orphaned = transform_material_units(
            units, materials, products_by_material, log
        )

        assert len(result) == 0
        assert len(orphaned) == 1
        assert log.material_units_orphaned == 1

    def test_new_format_units_pass_through(self, sample_materials, sample_products):
        materials = {m["slug"]: m for m in sample_materials}
        products_by_material = build_products_by_material_lookup(sample_products)
        log = MigrationLog()

        # Already new format
        units = [
            {
                "material_product_slug": "michaels-red-25m",
                "name": "6-inch cut",
                "slug": "6-inch-cut",
            }
        ]
        result, orphaned = transform_material_units(
            units, materials, products_by_material, log
        )

        assert len(result) == 1
        assert result[0]["material_product_slug"] == "michaels-red-25m"
        assert len(orphaned) == 0

    def test_handles_slug_collisions(self, sample_materials, sample_products):
        materials = {m["slug"]: m for m in sample_materials}
        products_by_material = build_products_by_material_lookup(sample_products)
        log = MigrationLog()

        # Two units with same slug for same material
        units = [
            {"material_slug": "red-ribbon", "name": "Cut A", "slug": "cut"},
            {"material_slug": "red-ribbon", "name": "Cut B", "slug": "cut"},
        ]
        result, _ = transform_material_units(
            units, materials, products_by_material, log
        )

        # Each unit duplicated to 2 products = 4 total
        # But slugs should be unique per product
        slugs_for_michaels = [
            u["slug"] for u in result if u["material_product_slug"] == "michaels-red-25m"
        ]
        assert len(slugs_for_michaels) == 2
        assert len(set(slugs_for_michaels)) == 2  # All unique

    def test_preserves_quantity_and_description(self, sample_materials, sample_products):
        materials = {m["slug"]: m for m in sample_materials}
        products_by_material = build_products_by_material_lookup(sample_products)
        log = MigrationLog()

        units = [
            {
                "material_slug": "clear-bags",  # Maps to 1 product
                "name": "Single Bag",
                "slug": "single-bag",
                "quantity_per_unit": 1.5,
                "description": "A clear bag",
            }
        ]
        result, _ = transform_material_units(
            units, materials, products_by_material, log
        )

        assert len(result) == 1
        assert result[0]["quantity_per_unit"] == 1.5
        assert result[0]["description"] == "A clear bag"


# ============================================================================
# Transform Compositions Tests
# ============================================================================


class TestTransformCompositions:
    def test_skips_compositions_with_material_slug(self):
        log = MigrationLog()
        compositions = [
            {
                "finished_good_slug": "box-a",
                "material_slug": "red-ribbon",
                "component_quantity": 2,
            },
            {
                "finished_good_slug": "box-b",
                "material_unit_slug": "6-inch-cut",
                "component_quantity": 1,
            },
        ]

        result = transform_compositions(compositions, log)

        assert len(result) == 1
        assert result[0]["finished_good_slug"] == "box-b"
        assert log.compositions_skipped == 1

    def test_passes_valid_compositions(self):
        log = MigrationLog()
        compositions = [
            {"finished_good_slug": "box-a", "material_unit_slug": "6-inch-cut"},
            {"finished_good_slug": "box-b", "finished_unit_slug": "cookie-dozen"},
        ]

        result = transform_compositions(compositions, log)

        assert len(result) == 2
        assert log.compositions_skipped == 0

    def test_handles_package_compositions(self):
        log = MigrationLog()
        compositions = [
            {"package_name": "Gift Pack", "material_slug": "red-ribbon"},
            {"package_name": "Standard Pack", "finished_unit_slug": "brownie-batch"},
        ]

        result = transform_compositions(compositions, log)

        assert len(result) == 1
        assert result[0]["package_name"] == "Standard Pack"
        assert log.compositions_skipped == 1


# ============================================================================
# Full Transform Tests
# ============================================================================


class TestFullTransform:
    def test_full_export_transformation(
        self, sample_materials, sample_products, sample_units_old_format
    ):
        data = {
            "materials": sample_materials,
            "material_products": sample_products,
            "material_units": sample_units_old_format,
            "compositions": [
                {"finished_good_slug": "box", "material_slug": "red-ribbon"},
            ],
            "other_data": ["should", "pass", "through"],
        }
        log = MigrationLog()

        result, orphaned = transform_export_data(data, log)

        assert "material_units" in result
        assert len(result["material_units"]) == 3  # 2 + 1 duplicates
        assert "compositions" in result
        assert len(result["compositions"]) == 0  # All skipped
        assert log.compositions_skipped == 1
        assert "other_data" in result  # Other data preserved
        assert len(orphaned) == 0

    def test_preserves_other_fields(self, sample_materials, sample_products):
        data = {
            "version": "4.1",
            "exported_at": "2025-01-01T00:00:00Z",
            "materials": sample_materials,
            "material_products": sample_products,
            "material_units": [],
            "compositions": [],
            "recipes": [{"name": "Test Recipe"}],
            "ingredients": [{"name": "Flour"}],
        }
        log = MigrationLog()

        result, _ = transform_export_data(data, log)

        assert result["version"] == "4.1"
        assert result["exported_at"] == "2025-01-01T00:00:00Z"
        assert result["recipes"] == [{"name": "Test Recipe"}]
        assert result["ingredients"] == [{"name": "Flour"}]


# ============================================================================
# Migration Log Tests
# ============================================================================


class TestMigrationLog:
    def test_log_decision_records_message(self):
        log = MigrationLog()
        log.log_decision("Test decision")

        assert len(log.decisions) == 1
        assert "Test decision" in log.decisions[0]

    def test_log_warning_records_message(self):
        log = MigrationLog()
        log.log_warning("Test warning")

        assert len(log.warnings) == 1
        assert "Test warning" in log.warnings[0]

    def test_log_error_records_message(self):
        log = MigrationLog()
        log.log_error("Test error")

        assert len(log.errors) == 1
        assert "Test error" in log.errors[0]

    def test_summary_includes_counts(self):
        log = MigrationLog()
        log.material_units_transformed = 10
        log.material_units_created = 15
        log.material_units_orphaned = 2
        log.compositions_skipped = 3

        summary = log.summary()

        assert "10" in summary
        assert "15" in summary
        assert "2" in summary
        assert "3" in summary
