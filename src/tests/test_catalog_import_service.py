"""
Tests for the Catalog Import Service.

Tests cover ingredient import with ADD_ONLY mode, validation,
and skip-existing behavior.
"""

import pytest
from src.services import catalog_import_service
from src.services.catalog_import_service import (
    CatalogImportResult,
    CatalogImportError,
    ImportMode,
    import_ingredients,
    import_products,
    import_recipes,
    import_catalog,
    validate_catalog_file,
)
from src.services.database import session_scope
from src.models.ingredient import Ingredient
from src.models.product import Product
from src.models.recipe import Recipe, RecipeIngredient, RecipeComponent


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


def _cleanup_test_data(session):
    """Helper to cleanup test data."""
    test_slugs = [
        "test_flour",
        "test_sugar",
        "test_butter",
        "existing_flour",
        "new_ingredient_1",
        "new_ingredient_2",
        "invalid_ingredient",
        "product_test_flour",
        "product_test_sugar",
        "recipe_test_flour",
        "recipe_test_sugar",
        "recipe_test_butter",
        # Include catalog_test_* patterns for E2E and integration tests
        "catalog_test_flour",
        "catalog_test_sugar",
        "catalog_test_butter",
        "catalog_test_eggs",
        "catalog_test_vanilla",
        "catalog_test_1",
        "catalog_test_2",
        "catalog_test_3",
        "catalog_test_4",
        "catalog_test_5",
    ]
    test_recipe_names = [
        "Test Chocolate Chip Cookies",
        "Test Sugar Cookies",
        "Test Vanilla Cake",
        "Test Chocolate Cake",
        "Test Frosting",
        "Test Composite Recipe",
        "Recipe A",
        "Recipe B",
        "Recipe C",
        "Catalog Test Cookies",
    ]
    # Delete recipe components first
    session.query(RecipeComponent).filter(
        RecipeComponent.recipe_id.in_(
            session.query(Recipe.id).filter(Recipe.name.in_(test_recipe_names))
        )
    ).delete(synchronize_session=False)
    # Delete recipe ingredients
    session.query(RecipeIngredient).filter(
        RecipeIngredient.recipe_id.in_(
            session.query(Recipe.id).filter(Recipe.name.in_(test_recipe_names))
        )
    ).delete(synchronize_session=False)
    # Delete recipes
    session.query(Recipe).filter(Recipe.name.in_(test_recipe_names)).delete(
        synchronize_session=False
    )
    # Delete products
    session.query(Product).filter(
        Product.ingredient_id.in_(
            session.query(Ingredient.id).filter(Ingredient.slug.in_(test_slugs))
        )
    ).delete(synchronize_session=False)
    # Delete ingredients
    session.query(Ingredient).filter(Ingredient.slug.in_(test_slugs)).delete(
        synchronize_session=False
    )


@pytest.fixture
def cleanup_test_ingredients(test_db):
    """Cleanup test ingredients and recipes after each test.

    Note: This fixture depends on test_db to ensure tests run against
    an in-memory database with the correct schema (package_unit, not purchase_unit).
    """
    yield
    # Cleanup after test
    with session_scope() as session:
        _cleanup_test_data(session)


@pytest.fixture
def sample_product_data():
    """Sample product data for testing (requires existing ingredient)."""
    return [
        {
            "ingredient_slug": "product_test_flour",
            "brand": "King Arthur",
            "package_size": "5 lb",
            "package_type": "bag",
            "package_unit": "bag",
            "package_unit_quantity": 5.0,
        },
        {
            "ingredient_slug": "product_test_flour",
            "brand": "Bob's Red Mill",
            "package_size": "2 lb",
            "package_unit": "bag",
            "package_unit_quantity": 2.0,
        },
    ]


@pytest.fixture
def create_test_ingredient_for_products(test_db):
    """Create a test ingredient for product import tests.

    Note: Depends on test_db to ensure correct schema is used.
    """
    with session_scope() as session:
        ingredient = Ingredient(
            slug="product_test_flour",
            display_name="Product Test Flour",
            category="Flour",
        )
        session.add(ingredient)
    yield
    # Cleanup handled by cleanup_test_ingredients


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

    def test_import_ingredients_augment_mode_updates_null_fields(
        self, cleanup_test_ingredients
    ):
        """Test that AUGMENT mode updates only null fields on existing records."""
        # Pre-create ingredient with some null fields
        with session_scope() as session:
            existing = Ingredient(
                slug="test_flour",
                display_name="Test Flour",
                category="Flour",
                density_volume_value=None,  # NULL - should be updated
                density_volume_unit=None,  # NULL - should be updated
            )
            session.add(existing)

        # Import with AUGMENT mode, providing density values
        data = [
            {
                "slug": "test_flour",
                "display_name": "Test Flour",
                "category": "Flour",
                "density_volume_value": 0.55,
                "density_volume_unit": "cup",
            }
        ]

        result = import_ingredients(data, mode="augment")

        # Verify augment count
        assert result.entity_counts["ingredients"].augmented == 1
        assert result.entity_counts["ingredients"].added == 0

        # Verify database updated
        with session_scope() as session:
            flour = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "test_flour")
                .first()
            )
            assert flour.density_volume_value == 0.55
            assert flour.density_volume_unit == "cup"

    def test_import_ingredients_augment_mode_preserves_existing_values(
        self, cleanup_test_ingredients
    ):
        """Test that AUGMENT mode does NOT overwrite non-null fields."""
        # Pre-create ingredient with existing density value
        with session_scope() as session:
            existing = Ingredient(
                slug="test_flour",
                display_name="Test Flour",
                category="Flour",
                density_volume_value=0.50,  # NOT NULL - should be preserved
                density_volume_unit="cup",  # NOT NULL - should be preserved
            )
            session.add(existing)

        # Try to import with AUGMENT mode, providing different density
        data = [
            {
                "slug": "test_flour",
                "display_name": "Test Flour",
                "category": "Flour",
                "density_volume_value": 0.99,  # Different value
                "density_volume_unit": "tablespoon",  # Different unit
            }
        ]

        result = import_ingredients(data, mode="augment")

        # Should skip since no null fields to update
        assert result.entity_counts["ingredients"].skipped == 1
        assert result.entity_counts["ingredients"].augmented == 0

        # Verify original values preserved
        with session_scope() as session:
            flour = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "test_flour")
                .first()
            )
            assert flour.density_volume_value == 0.50  # Original value preserved
            assert flour.density_volume_unit == "cup"  # Original value preserved

    def test_import_ingredients_augment_mode_creates_new(self, cleanup_test_ingredients):
        """Test that AUGMENT mode creates new records when slug doesn't exist."""
        data = [
            {
                "slug": "test_flour",
                "display_name": "Test Flour",
                "category": "Flour",
                "density_volume_value": 0.55,
            }
        ]

        result = import_ingredients(data, mode="augment")

        # Should add since record doesn't exist
        assert result.entity_counts["ingredients"].added == 1
        assert result.entity_counts["ingredients"].augmented == 0

        # Verify created
        with session_scope() as session:
            flour = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "test_flour")
                .first()
            )
            assert flour is not None
            assert flour.density_volume_value == 0.55


# ============================================================================
# Product Import Tests
# ============================================================================


class TestImportProducts:
    """Tests for import_products function."""

    def test_import_products_add_mode_creates_new(
        self,
        sample_product_data,
        create_test_ingredient_for_products,
        cleanup_test_ingredients,
    ):
        """Test that new products are created correctly with valid FK."""
        result = import_products(sample_product_data, mode="add")

        # Verify counts
        assert result.entity_counts["products"].added == 2
        assert result.entity_counts["products"].skipped == 0
        assert result.entity_counts["products"].failed == 0
        assert result.has_errors is False

        # Verify products exist in database with correct ingredient_id
        with session_scope() as session:
            ingredient = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "product_test_flour")
                .first()
            )
            assert ingredient is not None

            products = (
                session.query(Product)
                .filter(Product.ingredient_id == ingredient.id)
                .all()
            )
            assert len(products) == 2

            # Verify product details
            brands = {p.brand for p in products}
            assert "King Arthur" in brands
            assert "Bob's Red Mill" in brands

    def test_import_products_fk_validation_fails_on_missing_ingredient(
        self, cleanup_test_ingredients
    ):
        """Test that FK validation fails with actionable error when ingredient not found."""
        data = [
            {
                "ingredient_slug": "nonexistent_ingredient",
                "brand": "Test Brand",
                "package_unit": "bag",
                "package_unit_quantity": 5.0,
            }
        ]

        result = import_products(data, mode="add")

        # Verify counts
        assert result.entity_counts["products"].added == 0
        assert result.entity_counts["products"].failed == 1
        assert result.has_errors is True

        # Verify error message format
        assert len(result.errors) == 1
        error = result.errors[0]
        assert error.error_type == "fk_missing"
        assert "nonexistent_ingredient" in error.message
        assert "Import the ingredient first" in error.suggestion

    def test_import_products_skip_existing(
        self, create_test_ingredient_for_products, cleanup_test_ingredients
    ):
        """Test that existing products are skipped in ADD_ONLY mode."""
        # First import creates the product
        data = [
            {
                "ingredient_slug": "product_test_flour",
                "brand": "Existing Brand",
                "package_unit": "bag",
                "package_unit_quantity": 5.0,
            }
        ]
        result1 = import_products(data, mode="add")
        assert result1.entity_counts["products"].added == 1

        # Second import should skip
        result2 = import_products(data, mode="add")
        assert result2.entity_counts["products"].added == 0
        assert result2.entity_counts["products"].skipped == 1
        assert "Already exists" in result2.warnings[0]

    def test_import_products_null_brand_is_valid_unique_key(
        self, create_test_ingredient_for_products, cleanup_test_ingredients
    ):
        """Test that null brand is handled correctly as a valid unique key."""
        data = [
            {
                "ingredient_slug": "product_test_flour",
                "brand": None,  # Generic product
                "package_unit": "lb",
                "package_unit_quantity": 1.0,
            }
        ]

        result = import_products(data, mode="add")
        assert result.entity_counts["products"].added == 1

        # Try to import again with null brand - should skip
        result2 = import_products(data, mode="add")
        assert result2.entity_counts["products"].skipped == 1

    def test_import_products_different_brands_same_ingredient(
        self, create_test_ingredient_for_products, cleanup_test_ingredients
    ):
        """Test that different brands for same ingredient are separate products."""
        data = [
            {
                "ingredient_slug": "product_test_flour",
                "brand": "Brand A",
                "package_unit": "bag",
                "package_unit_quantity": 5.0,
            },
            {
                "ingredient_slug": "product_test_flour",
                "brand": "Brand B",
                "package_unit": "bag",
                "package_unit_quantity": 5.0,
            },
            {
                "ingredient_slug": "product_test_flour",
                "brand": None,  # Generic
                "package_unit": "lb",
                "package_unit_quantity": 1.0,
            },
        ]

        result = import_products(data, mode="add")
        assert result.entity_counts["products"].added == 3

    def test_import_products_validation_missing_package_unit(
        self, create_test_ingredient_for_products, cleanup_test_ingredients
    ):
        """Test that missing package_unit triggers validation error."""
        data = [
            {
                "ingredient_slug": "product_test_flour",
                "brand": "Test Brand",
                "package_unit_quantity": 5.0,
                # Missing package_unit
            }
        ]

        result = import_products(data, mode="add")
        assert result.entity_counts["products"].failed == 1
        assert "package_unit" in result.errors[0].message.lower()

    def test_import_products_validation_missing_package_unit_quantity(
        self, create_test_ingredient_for_products, cleanup_test_ingredients
    ):
        """Test that missing package_unit_quantity triggers validation error."""
        data = [
            {
                "ingredient_slug": "product_test_flour",
                "brand": "Test Brand",
                "package_unit": "bag",
                # Missing package_unit_quantity
            }
        ]

        result = import_products(data, mode="add")
        assert result.entity_counts["products"].failed == 1
        assert "package_unit_quantity" in result.errors[0].message.lower()

    def test_import_products_partial_success(
        self, create_test_ingredient_for_products, cleanup_test_ingredients
    ):
        """Test that valid products are imported even when some fail."""
        data = [
            {
                "ingredient_slug": "product_test_flour",
                "brand": "Valid Brand",
                "package_unit": "bag",
                "package_unit_quantity": 5.0,
            },
            {
                # Missing ingredient_slug - will fail
                "brand": "Invalid Brand",
                "package_unit": "bag",
                "package_unit_quantity": 5.0,
            },
            {
                "ingredient_slug": "product_test_flour",
                "brand": "Another Valid Brand",
                "package_unit": "bag",
                "package_unit_quantity": 2.0,
            },
        ]

        result = import_products(data, mode="add")
        assert result.entity_counts["products"].added == 2
        assert result.entity_counts["products"].failed == 1

    def test_import_products_dry_run_no_commit(
        self,
        sample_product_data,
        create_test_ingredient_for_products,
        cleanup_test_ingredients,
    ):
        """Test that dry_run does not commit changes to database."""
        result = import_products(sample_product_data, mode="add", dry_run=True)

        assert result.entity_counts["products"].added == 2
        assert result.dry_run is True

        # But nothing should be in the database
        with session_scope() as session:
            ingredient = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "product_test_flour")
                .first()
            )
            products = (
                session.query(Product)
                .filter(Product.ingredient_id == ingredient.id)
                .all()
            )
            assert len(products) == 0

    def test_import_products_with_optional_fields(
        self, create_test_ingredient_for_products, cleanup_test_ingredients
    ):
        """Test import with all optional fields populated."""
        data = [
            {
                "ingredient_slug": "product_test_flour",
                "brand": "Full Featured Brand",
                "package_size": "25 lb",
                "package_type": "bag",
                "package_unit": "bag",
                "package_unit_quantity": 25.0,
                "upc_code": "123456789012",
                "preferred": True,
            }
        ]

        result = import_products(data, mode="add")
        assert result.entity_counts["products"].added == 1

        with session_scope() as session:
            ingredient = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "product_test_flour")
                .first()
            )
            product = (
                session.query(Product)
                .filter(Product.ingredient_id == ingredient.id)
                .first()
            )
            assert product.brand == "Full Featured Brand"
            assert product.package_size == "25 lb"
            assert product.package_type == "bag"
            assert product.upc_code == "123456789012"
            assert product.preferred is True

    def test_import_products_with_session_parameter(
        self, create_test_ingredient_for_products, cleanup_test_ingredients
    ):
        """Test that session parameter works for transactional composition."""
        data = [
            {
                "ingredient_slug": "product_test_flour",
                "brand": "Session Test Brand",
                "package_unit": "bag",
                "package_unit_quantity": 5.0,
            }
        ]

        with session_scope() as session:
            result = import_products(data, mode="add", session=session)
            assert result.entity_counts["products"].added == 1

            # Within the same session, we can query the new product
            ingredient = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "product_test_flour")
                .first()
            )
            product = (
                session.query(Product)
                .filter(Product.ingredient_id == ingredient.id)
                .first()
            )
            assert product is not None
            assert product.brand == "Session Test Brand"

    def test_import_products_augment_mode_updates_null_fields(
        self, create_test_ingredient_for_products, cleanup_test_ingredients
    ):
        """Test that AUGMENT mode updates only null fields on existing products."""
        # Pre-create product with null upc_code
        with session_scope() as session:
            ingredient = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "product_test_flour")
                .first()
            )
            existing = Product(
                ingredient_id=ingredient.id,
                brand="Test Brand",
                package_unit="bag",
                package_unit_quantity=5.0,
                upc_code=None,  # NULL - should be updated
            )
            session.add(existing)

        # Import with AUGMENT mode
        # Must include package_unit_quantity and package_unit for matching
        data = [
            {
                "ingredient_slug": "product_test_flour",
                "brand": "Test Brand",
                "package_unit": "bag",
                "package_unit_quantity": 5.0,
                "upc_code": "123456789012",
            }
        ]

        result = import_products(data, mode="augment")

        # Verify augment count
        assert result.entity_counts["products"].augmented == 1

        # Verify database updated
        with session_scope() as session:
            ingredient = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "product_test_flour")
                .first()
            )
            product = (
                session.query(Product)
                .filter(Product.ingredient_id == ingredient.id)
                .filter(Product.brand == "Test Brand")
                .first()
            )
            assert product.upc_code == "123456789012"

    def test_import_products_augment_mode_preserves_existing_values(
        self, create_test_ingredient_for_products, cleanup_test_ingredients
    ):
        """Test that AUGMENT mode does NOT overwrite non-null fields."""
        # Pre-create product with existing upc_code
        with session_scope() as session:
            ingredient = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "product_test_flour")
                .first()
            )
            existing = Product(
                ingredient_id=ingredient.id,
                brand="Test Brand",
                package_unit="bag",
                package_unit_quantity=5.0,
                upc_code="000000000000",  # NOT NULL - should be preserved
            )
            session.add(existing)

        # Try to import with AUGMENT mode
        # Must include package_unit_quantity and package_unit for matching
        data = [
            {
                "ingredient_slug": "product_test_flour",
                "brand": "Test Brand",
                "package_unit": "bag",
                "package_unit_quantity": 5.0,
                "upc_code": "999999999999",  # Different value
            }
        ]

        result = import_products(data, mode="augment")

        # Should skip since no null fields to update
        assert result.entity_counts["products"].skipped == 1

        # Verify original value preserved
        with session_scope() as session:
            ingredient = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "product_test_flour")
                .first()
            )
            product = (
                session.query(Product)
                .filter(Product.ingredient_id == ingredient.id)
                .filter(Product.brand == "Test Brand")
                .first()
            )
            assert product.upc_code == "000000000000"  # Original value preserved

    def test_import_products_augment_mode_creates_new(
        self, create_test_ingredient_for_products, cleanup_test_ingredients
    ):
        """Test that AUGMENT mode creates new products when key doesn't exist."""
        data = [
            {
                "ingredient_slug": "product_test_flour",
                "brand": "New Brand",
                "package_unit": "bag",
                "package_unit_quantity": 10.0,
                "upc_code": "123456789012",
            }
        ]

        result = import_products(data, mode="augment")

        # Should add since record doesn't exist
        assert result.entity_counts["products"].added == 1
        assert result.entity_counts["products"].augmented == 0

        # Verify created
        with session_scope() as session:
            ingredient = (
                session.query(Ingredient)
                .filter(Ingredient.slug == "product_test_flour")
                .first()
            )
            product = (
                session.query(Product)
                .filter(Product.ingredient_id == ingredient.id)
                .filter(Product.brand == "New Brand")
                .first()
            )
            assert product is not None
            assert product.upc_code == "123456789012"


# ============================================================================
# Recipe Import Tests
# ============================================================================


@pytest.fixture
def create_test_ingredients_for_recipes(test_db):
    """Create test ingredients for recipe import tests.

    Note: Depends on test_db to ensure correct schema is used.
    """
    with session_scope() as session:
        flour = Ingredient(
            slug="recipe_test_flour",
            display_name="Recipe Test Flour",
            category="Flour",
        )
        sugar = Ingredient(
            slug="recipe_test_sugar",
            display_name="Recipe Test Sugar",
            category="Sugar",
        )
        butter = Ingredient(
            slug="recipe_test_butter",
            display_name="Recipe Test Butter",
            category="Dairy",
        )
        session.add_all([flour, sugar, butter])
    yield


class TestImportRecipes:
    """Tests for import_recipes function."""

    def test_import_recipes_add_mode_creates_new(
        self, create_test_ingredients_for_recipes, cleanup_test_ingredients
    ):
        """Test that new recipes are created correctly with all relationships."""
        data = [
            {
                "name": "Test Chocolate Chip Cookies",
                "category": "Cookies",
                "yield_quantity": 24,
                "yield_unit": "cookies",
                "ingredients": [
                    {"ingredient_slug": "recipe_test_flour", "quantity": 2.0, "unit": "cup"},
                    {"ingredient_slug": "recipe_test_sugar", "quantity": 1.0, "unit": "cup"},
                    {"ingredient_slug": "recipe_test_butter", "quantity": 0.5, "unit": "cup"},
                ],
            }
        ]

        result = import_recipes(data, mode="add")

        # Verify counts
        assert result.entity_counts["recipes"].added == 1
        assert result.entity_counts["recipes"].failed == 0
        assert result.has_errors is False

        # Verify recipe exists with correct relationships
        with session_scope() as session:
            recipe = (
                session.query(Recipe)
                .filter(Recipe.name == "Test Chocolate Chip Cookies")
                .first()
            )
            assert recipe is not None
            assert recipe.category == "Cookies"
            assert recipe.yield_quantity == 24
            assert recipe.yield_unit == "cookies"
            assert len(recipe.recipe_ingredients) == 3

    def test_import_recipes_fk_validation_fails_on_missing_ingredient(
        self, cleanup_test_ingredients
    ):
        """Test that FK validation fails with actionable error when ingredient not found."""
        data = [
            {
                "name": "Test Sugar Cookies",
                "category": "Cookies",
                "yield_quantity": 12,
                "yield_unit": "cookies",
                "ingredients": [
                    {"ingredient_slug": "missing_vanilla", "quantity": 1.0, "unit": "tsp"},
                ],
            }
        ]

        result = import_recipes(data, mode="add")

        # Verify counts
        assert result.entity_counts["recipes"].added == 0
        assert result.entity_counts["recipes"].failed == 1
        assert result.has_errors is True

        # Verify error message format
        assert len(result.errors) == 1
        error = result.errors[0]
        assert error.error_type == "fk_missing"
        assert "missing_vanilla" in error.message
        assert "Import these ingredients first" in error.suggestion

    def test_import_recipes_collision_with_detailed_error(
        self, create_test_ingredients_for_recipes, cleanup_test_ingredients
    ):
        """Test that collision error includes detailed info about both recipes."""
        # Pre-create recipe with name "Test Chocolate Cake"
        with session_scope() as session:
            existing = Recipe(
                name="Test Chocolate Cake",
                category="Cakes",
                yield_quantity=12,
                yield_unit="servings",
            )
            session.add(existing)

        # Try to import with same name but different yield
        data = [
            {
                "name": "Test Chocolate Cake",
                "category": "Cakes",
                "yield_quantity": 24,
                "yield_unit": "pieces",
                "ingredients": [],
            }
        ]

        result = import_recipes(data, mode="add")

        # Verify counts
        assert result.entity_counts["recipes"].failed == 1
        assert result.has_errors is True

        # Verify collision error includes both yield infos
        error = result.errors[0]
        assert error.error_type == "collision"
        assert "12" in error.message and "servings" in error.message  # Existing
        assert "24" in error.message and "pieces" in error.message  # Import

    def test_import_recipes_circular_detection(self, cleanup_test_ingredients):
        """Test that circular references are detected."""
        # Create A -> B -> C -> A circular reference
        data = [
            {
                "name": "Recipe A",
                "category": "Test",
                "yield_quantity": 1,
                "yield_unit": "batch",
                "ingredients": [],
                "components": [{"recipe_name": "Recipe B"}],
            },
            {
                "name": "Recipe B",
                "category": "Test",
                "yield_quantity": 1,
                "yield_unit": "batch",
                "ingredients": [],
                "components": [{"recipe_name": "Recipe C"}],
            },
            {
                "name": "Recipe C",
                "category": "Test",
                "yield_quantity": 1,
                "yield_unit": "batch",
                "ingredients": [],
                "components": [{"recipe_name": "Recipe A"}],
            },
        ]

        result = import_recipes(data, mode="add")

        # Should fail with circular reference error
        assert result.has_errors is True
        assert len(result.errors) == 1
        error = result.errors[0]
        assert error.error_type == "circular_reference"
        assert "Circular reference detected" in error.message
        # Cycle path should be included
        assert "Recipe A" in error.message or "Recipe B" in error.message or "Recipe C" in error.message

    def test_import_recipes_with_components(
        self, create_test_ingredients_for_recipes, cleanup_test_ingredients
    ):
        """Test importing recipe with component recipes in correct order."""
        # Import frosting first, then cake that uses it
        data = [
            {
                "name": "Test Frosting",
                "category": "Frostings",
                "yield_quantity": 2,
                "yield_unit": "cups",
                "ingredients": [
                    {"ingredient_slug": "recipe_test_butter", "quantity": 0.5, "unit": "cup"},
                    {"ingredient_slug": "recipe_test_sugar", "quantity": 2.0, "unit": "cup"},
                ],
            },
            {
                "name": "Test Vanilla Cake",
                "category": "Cakes",
                "yield_quantity": 12,
                "yield_unit": "servings",
                "ingredients": [
                    {"ingredient_slug": "recipe_test_flour", "quantity": 3.0, "unit": "cup"},
                    {"ingredient_slug": "recipe_test_sugar", "quantity": 1.5, "unit": "cup"},
                ],
                "components": [
                    {"recipe_name": "Test Frosting", "quantity": 1.0},
                ],
            },
        ]

        result = import_recipes(data, mode="add")

        # Both should be created
        assert result.entity_counts["recipes"].added == 2
        assert result.has_errors is False

        # Verify component relationship
        with session_scope() as session:
            cake = session.query(Recipe).filter(Recipe.name == "Test Vanilla Cake").first()
            assert cake is not None
            assert len(cake.recipe_components) == 1
            assert cake.recipe_components[0].component_recipe.name == "Test Frosting"

    def test_import_recipes_augment_mode_rejected(self, cleanup_test_ingredients):
        """Test that AUGMENT mode returns error for recipes."""
        data = [
            {
                "name": "Test Sugar Cookies",
                "category": "Cookies",
                "yield_quantity": 12,
                "yield_unit": "cookies",
                "ingredients": [],
            }
        ]

        result = import_recipes(data, mode="augment")

        # Should fail with mode not supported error
        assert result.has_errors is True
        error = result.errors[0]
        assert error.error_type == "mode_not_supported"
        assert "AUGMENT mode is not supported for recipes" in error.message

    def test_import_recipes_validation_missing_name(self, cleanup_test_ingredients):
        """Test that missing name triggers validation error."""
        data = [
            {
                "category": "Cookies",
                "yield_quantity": 12,
                "yield_unit": "cookies",
                "ingredients": [],
            }
        ]

        result = import_recipes(data, mode="add")

        assert result.entity_counts["recipes"].failed == 1
        assert "name" in result.errors[0].message.lower()

    def test_import_recipes_validation_missing_yield(self, cleanup_test_ingredients):
        """Test that missing yield fields trigger validation error."""
        data = [
            {
                "name": "Test Cookies",
                "category": "Cookies",
                "ingredients": [],
            }
        ]

        result = import_recipes(data, mode="add")

        assert result.entity_counts["recipes"].failed == 1
        assert "yield" in result.errors[0].message.lower()

    def test_import_recipes_partial_success(
        self, create_test_ingredients_for_recipes, cleanup_test_ingredients
    ):
        """Test that valid recipes are imported even when some fail."""
        data = [
            {
                "name": "Test Chocolate Chip Cookies",
                "category": "Cookies",
                "yield_quantity": 24,
                "yield_unit": "cookies",
                "ingredients": [
                    {"ingredient_slug": "recipe_test_flour", "quantity": 2.0, "unit": "cup"},
                ],
            },
            {
                "name": "Invalid Recipe",
                "category": "Cookies",
                "yield_quantity": 12,
                "yield_unit": "cookies",
                "ingredients": [
                    {"ingredient_slug": "nonexistent_ingredient", "quantity": 1.0, "unit": "cup"},
                ],
            },
            {
                "name": "Test Sugar Cookies",
                "category": "Cookies",
                "yield_quantity": 18,
                "yield_unit": "cookies",
                "ingredients": [
                    {"ingredient_slug": "recipe_test_sugar", "quantity": 1.0, "unit": "cup"},
                ],
            },
        ]

        result = import_recipes(data, mode="add")

        # 2 added, 1 failed
        assert result.entity_counts["recipes"].added == 2
        assert result.entity_counts["recipes"].failed == 1

    def test_import_recipes_dry_run_no_commit(
        self, create_test_ingredients_for_recipes, cleanup_test_ingredients
    ):
        """Test that dry_run does not commit changes to database."""
        data = [
            {
                "name": "Test Chocolate Chip Cookies",
                "category": "Cookies",
                "yield_quantity": 24,
                "yield_unit": "cookies",
                "ingredients": [
                    {"ingredient_slug": "recipe_test_flour", "quantity": 2.0, "unit": "cup"},
                ],
            }
        ]

        result = import_recipes(data, mode="add", dry_run=True)

        assert result.entity_counts["recipes"].added == 1
        assert result.dry_run is True

        # But nothing should be in the database
        with session_scope() as session:
            recipe = (
                session.query(Recipe)
                .filter(Recipe.name == "Test Chocolate Chip Cookies")
                .first()
            )
            assert recipe is None

    def test_import_recipes_with_optional_fields(
        self, create_test_ingredients_for_recipes, cleanup_test_ingredients
    ):
        """Test import with all optional fields populated."""
        data = [
            {
                "name": "Test Chocolate Chip Cookies",
                "category": "Cookies",
                "source": "Grandma's Recipe Box",
                "yield_quantity": 24,
                "yield_unit": "cookies",
                "yield_description": "2-inch cookies",
                "estimated_time_minutes": 45,
                "notes": "Chill dough for best results",
                "ingredients": [
                    {
                        "ingredient_slug": "recipe_test_flour",
                        "quantity": 2.0,
                        "unit": "cup",
                        "notes": "sifted",
                    },
                ],
            }
        ]

        result = import_recipes(data, mode="add")
        assert result.entity_counts["recipes"].added == 1

        with session_scope() as session:
            recipe = (
                session.query(Recipe)
                .filter(Recipe.name == "Test Chocolate Chip Cookies")
                .first()
            )
            assert recipe.source == "Grandma's Recipe Box"
            assert recipe.yield_description == "2-inch cookies"
            assert recipe.estimated_time_minutes == 45
            assert recipe.notes == "Chill dough for best results"
            assert recipe.recipe_ingredients[0].notes == "sifted"


# ============================================================================
# Coordinator and Dry-Run Tests
# ============================================================================


import json
import tempfile
import os


class TestValidateCatalogFile:
    """Tests for validate_catalog_file function."""

    def test_valid_catalog_file(self):
        """Test that valid catalog file is accepted."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"version": "3.4", "ingredients": []}, f)
            temp_path = f.name

        try:
            data = validate_catalog_file(temp_path)
            assert data["version"] == "3.4"
        finally:
            os.unlink(temp_path)

    def test_file_not_found(self):
        """Test that FileNotFoundError raised for missing file."""
        with pytest.raises(FileNotFoundError):
            validate_catalog_file("/nonexistent/path/file.json")

    def test_invalid_json(self):
        """Test that invalid JSON raises CatalogImportError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name

        try:
            with pytest.raises(CatalogImportError) as exc_info:
                validate_catalog_file(temp_path)
            assert "Invalid JSON" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_version_2x_rejected(self):
        """Test that version 2.x format raises error (only 3.x supported)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"version": "2.0", "data": {}}, f)
            temp_path = f.name

        try:
            with pytest.raises(CatalogImportError) as exc_info:
                validate_catalog_file(temp_path)
            assert "Unsupported version" in str(exc_info.value)
            assert "3.x" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_missing_version_rejected(self):
        """Test that file without version field is rejected."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"random": "data"}, f)
            temp_path = f.name

        try:
            with pytest.raises(CatalogImportError) as exc_info:
                validate_catalog_file(temp_path)
            assert "Missing 'version'" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_unsupported_version_rejected(self):
        """Test that unsupported version is rejected."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"version": "4.0"}, f)
            temp_path = f.name

        try:
            with pytest.raises(CatalogImportError) as exc_info:
                validate_catalog_file(temp_path)
            assert "Unsupported version" in str(exc_info.value)
        finally:
            os.unlink(temp_path)


class TestImportCatalog:
    """Tests for import_catalog coordinator function."""

    def test_import_catalog_dependency_order(self, cleanup_test_ingredients):
        """Test that entities are processed in correct dependency order."""
        # Create catalog with product that references ingredient in same file
        catalog_data = {
            "version": "3.4",
            "ingredients": [
                {
                    "slug": "test_flour",
                    "display_name": "Test Flour",
                    "category": "Flour",
                }
            ],
            "products": [
                {
                    "ingredient_slug": "test_flour",
                    "brand": "Test Brand",
                    "package_unit": "bag",
                    "package_unit_quantity": 5.0,
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(catalog_data, f)
            temp_path = f.name

        try:
            result = import_catalog(temp_path, mode="add")

            # Both should be created because ingredients processed first
            assert result.entity_counts["ingredients"].added == 1
            assert result.entity_counts["products"].added == 1
            assert result.has_errors is False

            # Verify in database
            with session_scope() as session:
                ingredient = (
                    session.query(Ingredient)
                    .filter(Ingredient.slug == "test_flour")
                    .first()
                )
                assert ingredient is not None
                product = (
                    session.query(Product)
                    .filter(Product.ingredient_id == ingredient.id)
                    .first()
                )
                assert product is not None
        finally:
            os.unlink(temp_path)

    def test_dry_run_no_commit(self, cleanup_test_ingredients):
        """Test that dry_run makes no database changes."""
        # Get initial counts
        with session_scope() as session:
            initial_count = session.query(Ingredient).filter(
                Ingredient.slug.like("catalog_test_%")
            ).count()

        # Create catalog with multiple ingredients
        catalog_data = {
            "version": "3.4",
            "ingredients": [
                {"slug": "catalog_test_1", "display_name": "Catalog Test 1", "category": "Test"},
                {"slug": "catalog_test_2", "display_name": "Catalog Test 2", "category": "Test"},
                {"slug": "catalog_test_3", "display_name": "Catalog Test 3", "category": "Test"},
                {"slug": "catalog_test_4", "display_name": "Catalog Test 4", "category": "Test"},
                {"slug": "catalog_test_5", "display_name": "Catalog Test 5", "category": "Test"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(catalog_data, f)
            temp_path = f.name

        try:
            # Dry run - should show 5 added but not commit
            result = import_catalog(temp_path, mode="add", dry_run=True)
            assert result.entity_counts["ingredients"].added == 5
            assert result.dry_run is True

            # Verify nothing in database
            with session_scope() as session:
                count = session.query(Ingredient).filter(
                    Ingredient.slug.like("catalog_test_%")
                ).count()
                assert count == initial_count  # No change

            # Actual import - should commit
            result = import_catalog(temp_path, mode="add", dry_run=False)
            assert result.entity_counts["ingredients"].added == 5

            # Verify in database
            with session_scope() as session:
                count = session.query(Ingredient).filter(
                    Ingredient.slug.like("catalog_test_%")
                ).count()
                assert count == initial_count + 5

            # Cleanup for test fixture
            with session_scope() as session:
                session.query(Ingredient).filter(
                    Ingredient.slug.like("catalog_test_%")
                ).delete(synchronize_session=False)
        finally:
            os.unlink(temp_path)

    def test_partial_success(self, cleanup_test_ingredients):
        """Test that valid records are committed even when some fail."""
        catalog_data = {
            "version": "3.4",
            "ingredients": [
                {"slug": "test_flour", "display_name": "Test Flour", "category": "Flour"},
                {"slug": "test_sugar", "display_name": "Test Sugar", "category": "Sugar"},
            ],
            "products": [
                {
                    # This will fail - references non-existent ingredient
                    "ingredient_slug": "nonexistent_ingredient",
                    "brand": "Bad Brand",
                    "package_unit": "bag",
                    "package_unit_quantity": 5.0,
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(catalog_data, f)
            temp_path = f.name

        try:
            result = import_catalog(temp_path, mode="add")

            # Ingredients should succeed, product should fail
            assert result.entity_counts["ingredients"].added == 2
            assert result.entity_counts["products"].failed == 1
            assert result.has_errors is True

            # Verify ingredients in database
            with session_scope() as session:
                flour = (
                    session.query(Ingredient)
                    .filter(Ingredient.slug == "test_flour")
                    .first()
                )
                sugar = (
                    session.query(Ingredient)
                    .filter(Ingredient.slug == "test_sugar")
                    .first()
                )
                assert flour is not None
                assert sugar is not None
        finally:
            os.unlink(temp_path)

    def test_entity_filter(self, cleanup_test_ingredients):
        """Test that entity filter limits which entities are imported."""
        catalog_data = {
            "version": "3.4",
            "ingredients": [
                {"slug": "test_flour", "display_name": "Test Flour", "category": "Flour"},
            ],
            "products": [
                {
                    "ingredient_slug": "test_flour",
                    "brand": "Test Brand",
                    "package_unit": "bag",
                    "package_unit_quantity": 5.0,
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(catalog_data, f)
            temp_path = f.name

        try:
            # Import only ingredients
            result = import_catalog(temp_path, mode="add", entities=["ingredients"])

            assert result.entity_counts["ingredients"].added == 1
            assert result.entity_counts["products"].added == 0  # Not imported

            # Product should fail now because ingredient wasn't imported in products-only run
            # But since we already imported ingredients, let's verify products weren't touched
            with session_scope() as session:
                ingredient = (
                    session.query(Ingredient)
                    .filter(Ingredient.slug == "test_flour")
                    .first()
                )
                assert ingredient is not None
                products = (
                    session.query(Product)
                    .filter(Product.ingredient_id == ingredient.id)
                    .all()
                )
                assert len(products) == 0  # Products not imported
        finally:
            os.unlink(temp_path)

    def test_invalid_entity_filter(self):
        """Test that invalid entity types raise error."""
        with pytest.raises(CatalogImportError) as exc_info:
            import_catalog("/nonexistent", entities=["invalid_type"])
        assert "Invalid entity types" in str(exc_info.value)


# ============================================================================
# CLI Tests
# ============================================================================


class TestCLI:
    """Tests for the import_catalog CLI."""

    def test_cli_add_mode(self, cleanup_test_ingredients):
        """[T047] Test full CLI flow in add mode."""
        from src.utils.import_catalog import main, EXIT_SUCCESS

        # Create temp catalog file
        catalog_data = {
            "version": "3.4",
            "ingredients": [
                {
                    "slug": "test_flour",
                    "display_name": "Test Flour",
                    "category": "Flour",
                },
                {
                    "slug": "test_sugar",
                    "display_name": "Test Sugar",
                    "category": "Sugar",
                },
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(catalog_data, f)
            temp_path = f.name

        try:
            # Run CLI
            exit_code = main([temp_path, "--mode=add"])

            # Verify exit code
            assert exit_code == EXIT_SUCCESS

            # Verify records in database
            with session_scope() as session:
                flour = (
                    session.query(Ingredient)
                    .filter(Ingredient.slug == "test_flour")
                    .first()
                )
                sugar = (
                    session.query(Ingredient)
                    .filter(Ingredient.slug == "test_sugar")
                    .first()
                )
                assert flour is not None
                assert sugar is not None
        finally:
            os.unlink(temp_path)

    def test_cli_dry_run(self, cleanup_test_ingredients):
        """[T048] Test CLI dry-run produces output but no changes."""
        from src.utils.import_catalog import main, EXIT_SUCCESS
        import io
        import sys

        # Create temp catalog file
        catalog_data = {
            "version": "3.4",
            "ingredients": [
                {
                    "slug": "test_flour",
                    "display_name": "Test Flour",
                    "category": "Flour",
                },
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(catalog_data, f)
            temp_path = f.name

        try:
            # Capture stdout
            captured_output = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured_output

            try:
                # Run CLI with --dry-run
                exit_code = main([temp_path, "--dry-run"])
            finally:
                sys.stdout = old_stdout

            output = captured_output.getvalue()

            # Verify exit code
            assert exit_code == EXIT_SUCCESS

            # Verify dry-run header appears
            assert "DRY RUN" in output

            # Verify output shows adds
            assert "1 added" in output or "Added:" in output

            # Verify database unchanged
            with session_scope() as session:
                flour = (
                    session.query(Ingredient)
                    .filter(Ingredient.slug == "test_flour")
                    .first()
                )
                assert flour is None  # Should NOT exist because dry-run
        finally:
            os.unlink(temp_path)

    def test_cli_verbose(self, cleanup_test_ingredients):
        """[T049] Test verbose mode shows details."""
        from src.utils.import_catalog import main
        import io
        import sys

        # Pre-create an ingredient to trigger a skip
        with session_scope() as session:
            existing = Ingredient(
                slug="test_flour",
                display_name="Existing Flour",
                category="Flour",
            )
            session.add(existing)

        # Create temp catalog file with mix of new/existing
        catalog_data = {
            "version": "3.4",
            "ingredients": [
                {
                    "slug": "test_flour",  # Will be skipped (already exists)
                    "display_name": "Test Flour",
                    "category": "Flour",
                },
                {
                    "slug": "test_sugar",  # Will be added
                    "display_name": "Test Sugar",
                    "category": "Sugar",
                },
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(catalog_data, f)
            temp_path = f.name

        try:
            # Capture stdout
            captured_output = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured_output

            try:
                # Run CLI with --verbose
                exit_code = main([temp_path, "--verbose"])
            finally:
                sys.stdout = old_stdout

            output = captured_output.getvalue()

            # Verify we got some output
            assert len(output) > 0

            # Verbose should show skip details
            assert "Skipped" in output or "skipped" in output

        finally:
            os.unlink(temp_path)

    def test_cli_file_not_found(self):
        """Test CLI returns EXIT_INVALID_ARGS for non-existent file."""
        from src.utils.import_catalog import main, EXIT_INVALID_ARGS
        import io
        import sys

        # Capture stderr
        captured_err = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured_err

        try:
            exit_code = main(["/nonexistent/catalog.json"])
        finally:
            sys.stderr = old_stderr

        assert exit_code == EXIT_INVALID_ARGS
        assert "not found" in captured_err.getvalue().lower() or "Error" in captured_err.getvalue()

    def test_cli_partial_failure(self, cleanup_test_ingredients):
        """Test CLI returns EXIT_PARTIAL when some records fail."""
        from src.utils.import_catalog import main, EXIT_PARTIAL

        # Create temp catalog file with valid ingredient and invalid product
        catalog_data = {
            "version": "3.4",
            "ingredients": [
                {
                    "slug": "test_flour",
                    "display_name": "Test Flour",
                    "category": "Flour",
                },
            ],
            "products": [
                {
                    # This will fail - references non-existent ingredient
                    "ingredient_slug": "nonexistent_ingredient",
                    "brand": "Bad Brand",
                    "package_unit": "bag",
                    "package_unit_quantity": 5.0,
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(catalog_data, f)
            temp_path = f.name

        try:
            exit_code = main([temp_path])

            # Should return partial because ingredient succeeded but product failed
            assert exit_code == EXIT_PARTIAL
        finally:
            os.unlink(temp_path)

    def test_cli_entity_filter(self, cleanup_test_ingredients):
        """Test CLI --entity flag filters entities."""
        from src.utils.import_catalog import main, EXIT_SUCCESS

        # Create temp catalog file
        catalog_data = {
            "version": "3.4",
            "ingredients": [
                {
                    "slug": "test_flour",
                    "display_name": "Test Flour",
                    "category": "Flour",
                },
            ],
            "products": [
                {
                    "ingredient_slug": "test_flour",
                    "brand": "Test Brand",
                    "package_unit": "bag",
                    "package_unit_quantity": 5.0,
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(catalog_data, f)
            temp_path = f.name

        try:
            # Import only ingredients
            exit_code = main([temp_path, "--entity=ingredients"])
            assert exit_code == EXIT_SUCCESS

            # Verify only ingredients imported
            with session_scope() as session:
                flour = (
                    session.query(Ingredient)
                    .filter(Ingredient.slug == "test_flour")
                    .first()
                )
                assert flour is not None

                # Products should NOT exist (not imported)
                products = session.query(Product).filter(Product.ingredient_id == flour.id).all()
                assert len(products) == 0
        finally:
            os.unlink(temp_path)
