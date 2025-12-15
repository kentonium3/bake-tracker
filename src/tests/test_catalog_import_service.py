"""
Tests for the Catalog Import Service.

Tests cover ingredient import with ADD_ONLY mode, validation,
and skip-existing behavior.
"""

import pytest
from src.services import catalog_import_service
from src.services.catalog_import_service import (
    CatalogImportResult,
    ImportMode,
    import_ingredients,
)
from src.services.database import session_scope
from src.models.ingredient import Ingredient


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_ingredient_data():
    """Sample ingredient data for testing."""
    return [
        {
            "slug": "test_flour",
            "display_name": "Test All-Purpose Flour",
            "category": "Flour",
            "description": "A test flour ingredient",
            "is_packaging": False,
        },
        {
            "slug": "test_sugar",
            "display_name": "Test White Sugar",
            "category": "Sugar",
            "description": "A test sugar ingredient",
        },
        {
            "slug": "test_butter",
            "display_name": "Test Unsalted Butter",
            "category": "Dairy",
            "is_packaging": False,
            "density_volume_value": 1.0,
            "density_volume_unit": "cup",
            "density_weight_value": 8.0,
            "density_weight_unit": "oz",
        },
    ]


@pytest.fixture
def cleanup_test_ingredients():
    """Cleanup test ingredients after each test."""
    yield
    # Cleanup after test
    with session_scope() as session:
        test_slugs = [
            "test_flour",
            "test_sugar",
            "test_butter",
            "existing_flour",
            "new_ingredient_1",
            "new_ingredient_2",
            "invalid_ingredient",
        ]
        session.query(Ingredient).filter(Ingredient.slug.in_(test_slugs)).delete(
            synchronize_session=False
        )


# ============================================================================
# CatalogImportResult Tests
# ============================================================================


class TestCatalogImportResult:
    """Tests for the CatalogImportResult class."""

    def test_init_creates_entity_counts(self):
        """Verify result initializes with all entity types."""
        result = CatalogImportResult()
        assert "ingredients" in result.entity_counts
        assert "products" in result.entity_counts
        assert "recipes" in result.entity_counts

    def test_add_success_increments_added(self):
        """Verify add_success increments the correct counter."""
        result = CatalogImportResult()
        result.add_success("ingredients")
        result.add_success("ingredients")
        assert result.entity_counts["ingredients"].added == 2
        assert result.total_added == 2

    def test_add_skip_increments_skipped_and_adds_warning(self):
        """Verify add_skip increments counter and records warning."""
        result = CatalogImportResult()
        result.add_skip("ingredients", "test_slug", "Already exists")
        assert result.entity_counts["ingredients"].skipped == 1
        assert result.total_skipped == 1
        assert len(result.warnings) == 1
        assert "test_slug" in result.warnings[0]

    def test_add_error_increments_failed_and_records_error(self):
        """Verify add_error increments counter and records structured error."""
        result = CatalogImportResult()
        result.add_error(
            "ingredients",
            "bad_ingredient",
            "validation",
            "Missing category",
            "Add category field",
        )
        assert result.entity_counts["ingredients"].failed == 1
        assert result.total_failed == 1
        assert result.has_errors is True
        assert len(result.errors) == 1
        assert result.errors[0].identifier == "bad_ingredient"

    def test_add_augment_increments_augmented(self):
        """Verify add_augment increments the augmented counter."""
        result = CatalogImportResult()
        result.add_augment("ingredients", "test_slug", ["density_volume_value"])
        assert result.entity_counts["ingredients"].augmented == 1
        assert result.total_augmented == 1

    def test_total_processed_sums_all_counts(self):
        """Verify total_processed includes all categories."""
        result = CatalogImportResult()
        result.add_success("ingredients")
        result.add_skip("ingredients", "skipped", "test")
        result.add_error("products", "failed", "test", "error", "fix")
        result.add_augment("recipes", "augmented", ["field"])
        assert result.total_processed == 4

    def test_has_errors_false_when_no_errors(self):
        """Verify has_errors is False when no errors recorded."""
        result = CatalogImportResult()
        result.add_success("ingredients")
        assert result.has_errors is False

    def test_merge_combines_results(self):
        """Verify merge combines two results correctly."""
        result1 = CatalogImportResult()
        result1.add_success("ingredients")
        result1.add_success("ingredients")

        result2 = CatalogImportResult()
        result2.add_success("ingredients")
        result2.add_skip("products", "test", "reason")
        result2.add_error("recipes", "bad", "val", "msg", "fix")

        result1.merge(result2)
        assert result1.entity_counts["ingredients"].added == 3
        assert result1.entity_counts["products"].skipped == 1
        assert result1.entity_counts["recipes"].failed == 1
        assert len(result1.warnings) == 1
        assert len(result1.errors) == 1

    def test_get_summary_includes_mode_and_counts(self):
        """Verify get_summary produces readable output."""
        result = CatalogImportResult()
        result.mode = "add"
        result.add_success("ingredients")
        result.add_success("ingredients")
        result.add_skip("ingredients", "existing", "Already exists")

        summary = result.get_summary()
        assert "mode: add" in summary
        assert "2 added" in summary
        assert "1 skipped" in summary

    def test_get_summary_shows_dry_run_warning(self):
        """Verify dry run is clearly indicated in summary."""
        result = CatalogImportResult()
        result.dry_run = True
        summary = result.get_summary()
        assert "DRY RUN" in summary


# ============================================================================
# Ingredient Import Tests
# ============================================================================


class TestImportIngredients:
    """Tests for import_ingredients function."""

    def test_import_ingredients_add_mode_creates_new(
        self, sample_ingredient_data, cleanup_test_ingredients
    ):
        """Test that new ingredients are created correctly in ADD_ONLY mode."""
        result = import_ingredients(sample_ingredient_data, mode="add")

        # Verify counts
        assert result.entity_counts["ingredients"].added == 3
        assert result.entity_counts["ingredients"].skipped == 0
        assert result.entity_counts["ingredients"].failed == 0
        assert result.has_errors is False

        # Verify ingredients exist in database
        with session_scope() as session:
            flour = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "test_flour")
                .first()
            )
            assert flour is not None
            assert flour.display_name == "Test All-Purpose Flour"
            assert flour.category == "Flour"

            sugar = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "test_sugar")
                .first()
            )
            assert sugar is not None
            assert sugar.category == "Sugar"

            butter = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "test_butter")
                .first()
            )
            assert butter is not None
            assert butter.density_volume_value == 1.0
            assert butter.density_weight_value == 8.0

    def test_import_ingredients_skip_existing(self, cleanup_test_ingredients):
        """Test that existing ingredients are skipped in ADD_ONLY mode."""
        # Pre-create an ingredient
        with session_scope() as session:
            existing = Ingredient(
                slug="existing_flour",
                display_name="Existing Flour",
                category="Flour",
            )
            session.add(existing)

        # Try to import with existing and new ingredients
        data = [
            {
                "slug": "existing_flour",
                "display_name": "Different Flour Name",
                "category": "Different Category",
            },
            {
                "slug": "new_ingredient_1",
                "display_name": "New Ingredient 1",
                "category": "Test",
            },
            {
                "slug": "new_ingredient_2",
                "display_name": "New Ingredient 2",
                "category": "Test",
            },
        ]

        result = import_ingredients(data, mode="add")

        # Verify counts: 2 added, 1 skipped
        assert result.entity_counts["ingredients"].added == 2
        assert result.entity_counts["ingredients"].skipped == 1
        assert result.has_errors is False
        assert len(result.warnings) == 1
        assert "existing_flour" in result.warnings[0]

        # Verify existing ingredient unchanged
        with session_scope() as session:
            flour = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "existing_flour")
                .first()
            )
            assert flour.display_name == "Existing Flour"  # Not changed!
            assert flour.category == "Flour"  # Not changed!

    def test_import_ingredients_validation_missing_slug(self, cleanup_test_ingredients):
        """Test that missing slug triggers validation error."""
        data = [
            {
                "display_name": "No Slug Ingredient",
                "category": "Test",
            }
        ]

        result = import_ingredients(data, mode="add")

        assert result.entity_counts["ingredients"].failed == 1
        assert result.has_errors is True
        assert "slug" in result.errors[0].message.lower()

    def test_import_ingredients_validation_missing_category(
        self, cleanup_test_ingredients
    ):
        """Test that missing category triggers validation error."""
        data = [
            {
                "slug": "invalid_ingredient",
                "display_name": "No Category",
            }
        ]

        result = import_ingredients(data, mode="add")

        assert result.entity_counts["ingredients"].failed == 1
        assert result.has_errors is True
        assert "category" in result.errors[0].message.lower()

    def test_import_ingredients_validation_missing_display_name(
        self, cleanup_test_ingredients
    ):
        """Test that missing display_name triggers validation error."""
        data = [
            {
                "slug": "invalid_ingredient",
                "category": "Test",
            }
        ]

        result = import_ingredients(data, mode="add")

        assert result.entity_counts["ingredients"].failed == 1
        assert result.has_errors is True
        assert "display_name" in result.errors[0].message.lower()

    def test_import_ingredients_partial_success(self, cleanup_test_ingredients):
        """Test that valid ingredients are imported even when some fail."""
        data = [
            {
                "slug": "test_flour",
                "display_name": "Test Flour",
                "category": "Flour",
            },
            {
                # Missing required fields
                "slug": "invalid_ingredient",
            },
            {
                "slug": "test_sugar",
                "display_name": "Test Sugar",
                "category": "Sugar",
            },
        ]

        result = import_ingredients(data, mode="add")

        # 2 added, 1 failed
        assert result.entity_counts["ingredients"].added == 2
        assert result.entity_counts["ingredients"].failed == 1

        # Valid ingredients should exist
        with session_scope() as session:
            assert (
                session.query(Ingredient)
                .filter(Ingredient.slug == "test_flour")
                .first()
                is not None
            )
            assert (
                session.query(Ingredient)
                .filter(Ingredient.slug == "test_sugar")
                .first()
                is not None
            )

    def test_import_ingredients_dry_run_no_commit(
        self, sample_ingredient_data, cleanup_test_ingredients
    ):
        """Test that dry_run does not commit changes to database."""
        result = import_ingredients(sample_ingredient_data, mode="add", dry_run=True)

        # Counts should show what would happen
        assert result.entity_counts["ingredients"].added == 3
        assert result.dry_run is True

        # But nothing should be in the database
        with session_scope() as session:
            flour = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "test_flour")
                .first()
            )
            assert flour is None

    def test_import_ingredients_result_mode_tracking(self, cleanup_test_ingredients):
        """Test that result tracks the mode used."""
        data = [
            {
                "slug": "test_flour",
                "display_name": "Test Flour",
                "category": "Flour",
            }
        ]

        result = import_ingredients(data, mode="add")
        assert result.mode == "add"

    def test_import_ingredients_duplicate_within_import(self, cleanup_test_ingredients):
        """Test that duplicates within same import are handled."""
        data = [
            {
                "slug": "test_flour",
                "display_name": "Test Flour 1",
                "category": "Flour",
            },
            {
                "slug": "test_flour",  # Duplicate slug!
                "display_name": "Test Flour 2",
                "category": "Flour",
            },
        ]

        result = import_ingredients(data, mode="add")

        # First should be added, second should be skipped
        assert result.entity_counts["ingredients"].added == 1
        assert result.entity_counts["ingredients"].skipped == 1

    def test_import_ingredients_with_optional_fields(self, cleanup_test_ingredients):
        """Test import with all optional fields populated."""
        data = [
            {
                "slug": "test_butter",
                "display_name": "Test Butter",
                "category": "Dairy",
                "description": "Unsalted butter for baking",
                "is_packaging": False,
                "density_volume_value": 1.0,
                "density_volume_unit": "cup",
                "density_weight_value": 8.0,
                "density_weight_unit": "oz",
                "allergens": ["dairy"],
                "foodon_id": "FOODON:12345",
                "fdc_ids": ["12345", "67890"],
            }
        ]

        result = import_ingredients(data, mode="add")
        assert result.entity_counts["ingredients"].added == 1

        with session_scope() as session:
            butter = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "test_butter")
                .first()
            )
            assert butter.description == "Unsalted butter for baking"
            assert butter.density_volume_value == 1.0
            assert butter.density_volume_unit == "cup"
            assert butter.allergens == ["dairy"]
            assert butter.foodon_id == "FOODON:12345"
            assert butter.fdc_ids == ["12345", "67890"]

    def test_import_ingredients_with_session_parameter(self, cleanup_test_ingredients):
        """Test that session parameter works for transactional composition."""
        data = [
            {
                "slug": "test_flour",
                "display_name": "Test Flour",
                "category": "Flour",
            }
        ]

        with session_scope() as session:
            result = import_ingredients(data, mode="add", session=session)
            assert result.entity_counts["ingredients"].added == 1

            # Within the same session, we can query the new ingredient
            flour = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "test_flour")
                .first()
            )
            assert flour is not None

        # After session commits, verify it persisted
        with session_scope() as session:
            flour = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "test_flour")
                .first()
            )
            assert flour is not None
