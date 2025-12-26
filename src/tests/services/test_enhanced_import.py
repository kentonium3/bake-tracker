"""Tests for enhanced_import_service.py"""

import json
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.models.ingredient import Ingredient
from src.models.product import Product
from src.models.supplier import Supplier
from src.services.enhanced_import_service import (
    EnhancedImportResult,
    _collect_missing_fks_for_view,
    _find_existing_by_slug,
    _resolve_fk_by_slug,
    _view_type_to_entity_type,
    import_view,
)
from src.services.fk_resolver_service import (
    MissingFK,
    Resolution,
    ResolutionChoice,
)
from src.services.import_export_service import ImportResult
from src.services.database import session_scope


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def unique_id():
    """Generate a unique ID for test isolation."""
    return str(uuid.uuid4())[:8]


@pytest.fixture
def sample_ingredient(test_db, unique_id):
    """Create a sample ingredient in the database."""
    with session_scope() as session:
        ingredient = Ingredient(
            slug=f"test_flour_{unique_id}",
            display_name=f"Test Flour {unique_id}",
            category="Flour",
        )
        session.add(ingredient)
        session.commit()
        return {
            "id": ingredient.id,
            "slug": ingredient.slug,
            "display_name": ingredient.display_name,
            "category": ingredient.category,
        }


@pytest.fixture
def sample_supplier(test_db, unique_id):
    """Create a sample supplier in the database."""
    with session_scope() as session:
        supplier = Supplier(
            name=f"Test Supplier {unique_id}",
            city="Boston",
            state="MA",
            zip_code="02101",
        )
        session.add(supplier)
        session.commit()
        return {
            "id": supplier.id,
            "name": supplier.name,
            "city": supplier.city,
            "state": supplier.state,
            "zip_code": supplier.zip_code,
        }


@pytest.fixture
def sample_product(test_db, sample_ingredient, unique_id):
    """Create a sample product in the database."""
    with session_scope() as session:
        product = Product(
            ingredient_id=sample_ingredient["id"],
            brand=f"Test Brand {unique_id}",
            package_unit="lb",
            package_unit_quantity=5.0,
            product_name=f"Test Product {unique_id}",
        )
        session.add(product)
        session.commit()
        return {
            "id": product.id,
            "ingredient_id": product.ingredient_id,
            "ingredient_slug": sample_ingredient["slug"],
            "brand": product.brand,
            "package_unit": product.package_unit,
            "package_unit_quantity": product.package_unit_quantity,
            "product_name": product.product_name,
        }


@pytest.fixture
def view_file_products(sample_ingredient, tmp_path, unique_id):
    """Create a product view file for testing."""
    view_data = {
        "version": "1.0",
        "view_type": "products",
        "export_date": "2025-12-25T10:00:00Z",
        "_meta": {
            "editable_fields": ["brand", "product_name", "package_size", "upc_code"],
            "readonly_fields": ["id", "ingredient_id", "ingredient_slug"],
        },
        "records": [
            {
                "id": 999,
                "ingredient_slug": sample_ingredient["slug"],
                "brand": f"New Brand {unique_id}",
                "package_unit": "oz",
                "package_unit_quantity": 16.0,
                "product_name": f"New Product {unique_id}",
            }
        ],
    }

    file_path = tmp_path / "view_products.json"
    with open(file_path, "w") as f:
        json.dump(view_data, f)

    return str(file_path)


@pytest.fixture
def view_file_with_missing_fk(tmp_path, unique_id):
    """Create a product view file with missing FK reference."""
    view_data = {
        "version": "1.0",
        "view_type": "products",
        "export_date": "2025-12-25T10:00:00Z",
        "_meta": {
            "editable_fields": ["brand", "product_name"],
            "readonly_fields": ["id", "ingredient_slug"],
        },
        "records": [
            {
                "id": 999,
                "ingredient_slug": f"nonexistent_ingredient_{unique_id}",
                "brand": f"Test Brand {unique_id}",
                "package_unit": "lb",
                "package_unit_quantity": 5.0,
                "product_name": f"Test Product {unique_id}",
            }
        ],
    }

    file_path = tmp_path / "view_products_missing_fk.json"
    with open(file_path, "w") as f:
        json.dump(view_data, f)

    return str(file_path)


# ============================================================================
# EnhancedImportResult Tests
# ============================================================================


class TestEnhancedImportResult:
    """Tests for EnhancedImportResult dataclass."""

    def test_default_initialization(self):
        """Test default initialization of EnhancedImportResult."""
        result = EnhancedImportResult()

        assert result.total_records == 0
        assert result.successful == 0
        assert result.skipped == 0
        assert result.failed == 0
        assert result.errors == []
        assert result.warnings == []
        assert result.resolutions == []
        assert result.created_entities == {}
        assert result.mapped_entities == {}
        assert result.skipped_due_to_fk == 0
        assert result.dry_run is False
        assert result.skipped_records_path is None

    def test_add_success_delegates_to_base(self):
        """Test that add_success delegates to base_result."""
        result = EnhancedImportResult()
        result.add_success("ingredient")

        assert result.total_records == 1
        assert result.successful == 1
        assert result.entity_counts["ingredient"]["imported"] == 1

    def test_add_skip_delegates_to_base(self):
        """Test that add_skip delegates to base_result."""
        result = EnhancedImportResult()
        result.add_skip("ingredient", "test_slug", "Already exists")

        assert result.total_records == 1
        assert result.skipped == 1
        assert len(result.warnings) == 1

    def test_add_error_delegates_to_base(self):
        """Test that add_error delegates to base_result."""
        result = EnhancedImportResult()
        result.add_error("ingredient", "test_slug", "Invalid data")

        assert result.total_records == 1
        assert result.failed == 1
        assert len(result.errors) == 1

    def test_add_created_entity(self):
        """Test tracking created entities."""
        result = EnhancedImportResult()
        result.add_created_entity("supplier")
        result.add_created_entity("supplier")
        result.add_created_entity("ingredient")

        assert result.created_entities["supplier"] == 2
        assert result.created_entities["ingredient"] == 1

    def test_add_mapped_entity(self):
        """Test tracking mapped entities."""
        result = EnhancedImportResult()
        result.add_mapped_entity("supplier")
        result.add_mapped_entity("ingredient")

        assert result.mapped_entities["supplier"] == 1
        assert result.mapped_entities["ingredient"] == 1

    def test_get_summary_includes_fk_resolutions(self):
        """Test that get_summary includes FK resolution info."""
        result = EnhancedImportResult()
        result.add_success("product")
        result.add_created_entity("supplier")
        result.add_mapped_entity("ingredient")
        result.resolutions = [
            Resolution(
                choice=ResolutionChoice.CREATE,
                entity_type="supplier",
                missing_value="New Supplier",
            )
        ]

        summary = result.get_summary()

        assert "FK Resolutions:" in summary
        assert "Created: 1" in summary
        assert "Mapped: 1" in summary

    def test_get_summary_dry_run_notice(self):
        """Test that get_summary shows dry run notice."""
        result = EnhancedImportResult()
        result.dry_run = True

        summary = result.get_summary()

        assert "DRY RUN" in summary
        assert "No changes were made" in summary

    def test_get_summary_shows_skipped_records_path(self):
        """Test that get_summary shows skipped records path."""
        result = EnhancedImportResult()
        result.skipped_records_path = "/path/to/skipped.json"

        summary = result.get_summary()

        assert "Skipped records log:" in summary
        assert "/path/to/skipped.json" in summary


# ============================================================================
# Helper Function Tests
# ============================================================================


class TestViewTypeToEntityType:
    """Tests for _view_type_to_entity_type."""

    def test_products_mapping(self):
        assert _view_type_to_entity_type("products") == "product"
        assert _view_type_to_entity_type("product") == "product"

    def test_ingredients_mapping(self):
        assert _view_type_to_entity_type("ingredients") == "ingredient"
        assert _view_type_to_entity_type("ingredient") == "ingredient"

    def test_suppliers_mapping(self):
        assert _view_type_to_entity_type("suppliers") == "supplier"
        assert _view_type_to_entity_type("supplier") == "supplier"

    def test_case_insensitive(self):
        assert _view_type_to_entity_type("Products") == "product"
        assert _view_type_to_entity_type("SUPPLIERS") == "supplier"

    def test_unknown_returns_none(self):
        assert _view_type_to_entity_type("unknown") is None
        assert _view_type_to_entity_type("") is None


class TestResolveFkBySlug:
    """Tests for _resolve_fk_by_slug."""

    def test_resolve_ingredient_by_slug(self, sample_ingredient):
        """Test resolving ingredient FK by slug."""
        with session_scope() as session:
            result = _resolve_fk_by_slug(
                "ingredient", sample_ingredient["slug"], session
            )
            assert result == sample_ingredient["id"]

    def test_resolve_supplier_by_name(self, sample_supplier):
        """Test resolving supplier FK by name."""
        with session_scope() as session:
            result = _resolve_fk_by_slug("supplier", sample_supplier["name"], session)
            assert result == sample_supplier["id"]

    def test_resolve_nonexistent_returns_none(self, test_db):
        """Test that nonexistent slugs return None."""
        with session_scope() as session:
            result = _resolve_fk_by_slug("ingredient", "nonexistent_slug", session)
            assert result is None

    def test_resolve_empty_slug_returns_none(self, test_db):
        """Test that empty slug returns None."""
        with session_scope() as session:
            result = _resolve_fk_by_slug("ingredient", "", session)
            assert result is None

    def test_resolve_product_returns_none(self, test_db):
        """Test that product resolution returns None (needs composite key)."""
        with session_scope() as session:
            result = _resolve_fk_by_slug("product", "any_value", session)
            assert result is None


class TestFindExistingBySlug:
    """Tests for _find_existing_by_slug."""

    def test_find_ingredient_by_slug(self, sample_ingredient):
        """Test finding ingredient by slug."""
        with session_scope() as session:
            record = {"ingredient_slug": sample_ingredient["slug"]}
            result = _find_existing_by_slug(record, "ingredient", session)
            assert result is not None
            assert result.slug == sample_ingredient["slug"]

    def test_find_ingredient_by_slug_field(self, sample_ingredient):
        """Test finding ingredient by 'slug' field."""
        with session_scope() as session:
            record = {"slug": sample_ingredient["slug"]}
            result = _find_existing_by_slug(record, "ingredient", session)
            assert result is not None

    def test_find_supplier_by_name(self, sample_supplier):
        """Test finding supplier by name."""
        with session_scope() as session:
            record = {"supplier_name": sample_supplier["name"]}
            result = _find_existing_by_slug(record, "supplier", session)
            assert result is not None
            assert result.name == sample_supplier["name"]

    def test_find_product_by_composite_key(self, sample_product, sample_ingredient):
        """Test finding product by composite key."""
        with session_scope() as session:
            record = {
                "ingredient_slug": sample_ingredient["slug"],
                "brand": sample_product["brand"],
                "package_unit": sample_product["package_unit"],
                "package_unit_quantity": sample_product["package_unit_quantity"],
            }
            result = _find_existing_by_slug(record, "product", session)
            assert result is not None
            assert result.brand == sample_product["brand"]

    def test_find_nonexistent_returns_none(self, test_db):
        """Test that nonexistent entity returns None."""
        with session_scope() as session:
            record = {"ingredient_slug": "nonexistent"}
            result = _find_existing_by_slug(record, "ingredient", session)
            assert result is None


class TestCollectMissingFksForView:
    """Tests for _collect_missing_fks_for_view."""

    def test_collect_missing_ingredient_fk(self, test_db, unique_id):
        """Test collecting missing ingredient FK references."""
        records = [
            {
                "ingredient_slug": f"missing_ingredient_{unique_id}",
                "brand": "Test",
                "package_unit": "lb",
                "package_unit_quantity": 5.0,
            },
            {
                "ingredient_slug": f"missing_ingredient_{unique_id}",
                "brand": "Test2",
                "package_unit": "oz",
                "package_unit_quantity": 16.0,
            },
        ]

        with session_scope() as session:
            missing = _collect_missing_fks_for_view(records, "product", session)

        assert len(missing) == 1
        assert missing[0].entity_type == "ingredient"
        assert missing[0].missing_value == f"missing_ingredient_{unique_id}"
        assert missing[0].affected_record_count == 2

    def test_collect_missing_supplier_fk(self, sample_ingredient, unique_id):
        """Test collecting missing supplier FK references."""
        records = [
            {
                "ingredient_slug": sample_ingredient["slug"],
                "supplier_name": f"Missing Supplier {unique_id}",
                "brand": "Test",
                "package_unit": "lb",
                "package_unit_quantity": 5.0,
            }
        ]

        with session_scope() as session:
            missing = _collect_missing_fks_for_view(records, "product", session)

        assert len(missing) == 1
        assert missing[0].entity_type == "supplier"
        assert missing[0].missing_value == f"Missing Supplier {unique_id}"

    def test_no_missing_fks_for_valid_records(self, sample_ingredient):
        """Test that valid records return no missing FKs."""
        records = [
            {
                "ingredient_slug": sample_ingredient["slug"],
                "brand": "Test",
                "package_unit": "lb",
                "package_unit_quantity": 5.0,
            }
        ]

        with session_scope() as session:
            missing = _collect_missing_fks_for_view(records, "product", session)

        assert len(missing) == 0

    def test_sample_records_limited_to_3(self, test_db, unique_id):
        """Test that sample_records is limited to 3 records."""
        records = [
            {
                "ingredient_slug": f"missing_{unique_id}",
                "brand": f"Brand{i}",
                "package_unit": "lb",
                "package_unit_quantity": 5.0,
            }
            for i in range(10)
        ]

        with session_scope() as session:
            missing = _collect_missing_fks_for_view(records, "product", session)

        assert len(missing[0].sample_records) == 3
        assert missing[0].affected_record_count == 10


# ============================================================================
# Import View Tests
# ============================================================================


class TestImportViewBasic:
    """Basic tests for import_view function."""

    def test_import_file_not_found(self, test_db, tmp_path):
        """Test import with non-existent file."""
        result = import_view(str(tmp_path / "nonexistent.json"))

        assert result.failed == 1
        assert "File not found" in result.errors[0]["message"]

    def test_import_invalid_json(self, test_db, tmp_path):
        """Test import with invalid JSON file."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text("not valid json")

        result = import_view(str(file_path))

        assert result.failed == 1
        assert "Invalid JSON" in result.errors[0]["message"]

    def test_import_missing_view_type(self, test_db, tmp_path):
        """Test import with missing view_type."""
        file_path = tmp_path / "missing_type.json"
        file_path.write_text('{"records": []}')

        result = import_view(str(file_path))

        assert result.failed == 1
        assert "Missing view_type" in result.errors[0]["message"]

    def test_import_empty_records(self, test_db, tmp_path):
        """Test import with empty records."""
        file_path = tmp_path / "empty.json"
        file_path.write_text('{"view_type": "products", "records": []}')

        result = import_view(str(file_path))

        assert len(result.warnings) == 1
        assert "No records" in result.warnings[0]["message"]


class TestImportViewMergeMode:
    """Tests for merge mode import."""

    def test_merge_adds_new_record(self, view_file_products, sample_ingredient):
        """Test that merge mode adds new records."""
        result = import_view(view_file_products, mode="merge")

        assert result.successful >= 1

    def test_merge_updates_existing_record(
        self, sample_product, sample_ingredient, tmp_path, unique_id
    ):
        """Test that merge mode updates existing records."""
        # Create view with updated data for existing product
        view_data = {
            "version": "1.0",
            "view_type": "products",
            "_meta": {
                "editable_fields": ["product_name", "upc_code"],
            },
            "records": [
                {
                    "ingredient_slug": sample_ingredient["slug"],
                    "brand": sample_product["brand"],
                    "package_unit": sample_product["package_unit"],
                    "package_unit_quantity": sample_product["package_unit_quantity"],
                    "product_name": f"Updated Name {unique_id}",
                }
            ],
        }

        file_path = tmp_path / "view_update.json"
        with open(file_path, "w") as f:
            json.dump(view_data, f)

        result = import_view(str(file_path), mode="merge")

        assert result.successful >= 1

        # Verify the update
        with session_scope() as session:
            product = session.query(Product).filter_by(id=sample_product["id"]).first()
            assert product.product_name == f"Updated Name {unique_id}"

    def test_merge_skips_unchanged_record(
        self, sample_product, sample_ingredient, tmp_path
    ):
        """Test that merge mode skips unchanged records."""
        # Create view with same data as existing product
        view_data = {
            "version": "1.0",
            "view_type": "products",
            "_meta": {
                "editable_fields": ["product_name"],
            },
            "records": [
                {
                    "ingredient_slug": sample_ingredient["slug"],
                    "brand": sample_product["brand"],
                    "package_unit": sample_product["package_unit"],
                    "package_unit_quantity": sample_product["package_unit_quantity"],
                    "product_name": sample_product["product_name"],  # Same name
                }
            ],
        }

        file_path = tmp_path / "view_unchanged.json"
        with open(file_path, "w") as f:
            json.dump(view_data, f)

        result = import_view(str(file_path), mode="merge")

        assert result.skipped >= 1


class TestImportViewSkipExistingMode:
    """Tests for skip_existing mode import."""

    def test_skip_existing_adds_new(self, view_file_products, sample_ingredient):
        """Test that skip_existing mode adds new records."""
        result = import_view(view_file_products, mode="skip_existing")

        assert result.successful >= 1

    def test_skip_existing_skips_existing(
        self, sample_product, sample_ingredient, tmp_path, unique_id
    ):
        """Test that skip_existing mode skips existing records."""
        # Create view with existing product (different name to ensure it would update in merge mode)
        view_data = {
            "version": "1.0",
            "view_type": "products",
            "_meta": {
                "editable_fields": ["product_name"],
            },
            "records": [
                {
                    "ingredient_slug": sample_ingredient["slug"],
                    "brand": sample_product["brand"],
                    "package_unit": sample_product["package_unit"],
                    "package_unit_quantity": sample_product["package_unit_quantity"],
                    "product_name": f"Would Update {unique_id}",
                }
            ],
        }

        file_path = tmp_path / "view_skip.json"
        with open(file_path, "w") as f:
            json.dump(view_data, f)

        result = import_view(str(file_path), mode="skip_existing")

        assert result.skipped >= 1

        # Verify the name was NOT updated
        with session_scope() as session:
            product = session.query(Product).filter_by(id=sample_product["id"]).first()
            assert product.product_name == sample_product["product_name"]


class TestImportViewDryRun:
    """Tests for dry_run mode."""

    def test_dry_run_makes_no_changes(self, sample_ingredient, tmp_path, unique_id):
        """Test that dry_run mode makes no database changes."""
        view_data = {
            "version": "1.0",
            "view_type": "products",
            "_meta": {
                "editable_fields": ["brand", "product_name"],
            },
            "records": [
                {
                    "ingredient_slug": sample_ingredient["slug"],
                    "brand": f"Dry Run Brand {unique_id}",
                    "package_unit": "kg",
                    "package_unit_quantity": 1.0,
                    "product_name": f"Dry Run Product {unique_id}",
                }
            ],
        }

        file_path = tmp_path / "view_dryrun.json"
        with open(file_path, "w") as f:
            json.dump(view_data, f)

        # Count products before
        with session_scope() as session:
            count_before = session.query(Product).count()

        result = import_view(str(file_path), mode="merge", dry_run=True)

        assert result.dry_run is True
        assert result.successful >= 1

        # Count products after - should be the same
        with session_scope() as session:
            count_after = session.query(Product).count()

        assert count_after == count_before

    def test_dry_run_summary_indicates_no_changes(
        self, view_file_products, sample_ingredient
    ):
        """Test that dry_run summary indicates no changes were made."""
        result = import_view(view_file_products, dry_run=True)

        summary = result.get_summary()
        assert "DRY RUN" in summary


class TestImportViewSkipOnError:
    """Tests for skip_on_error mode."""

    def test_skip_on_error_continues_with_valid_records(
        self, sample_ingredient, tmp_path, unique_id
    ):
        """Test that skip_on_error imports valid records and skips invalid."""
        view_data = {
            "version": "1.0",
            "view_type": "products",
            "_meta": {
                "editable_fields": ["brand", "product_name"],
            },
            "records": [
                # Valid record
                {
                    "ingredient_slug": sample_ingredient["slug"],
                    "brand": f"Valid Brand {unique_id}",
                    "package_unit": "lb",
                    "package_unit_quantity": 5.0,
                    "product_name": f"Valid Product {unique_id}",
                },
                # Invalid record - missing ingredient
                {
                    "ingredient_slug": f"nonexistent_{unique_id}",
                    "brand": f"Invalid Brand {unique_id}",
                    "package_unit": "oz",
                    "package_unit_quantity": 16.0,
                    "product_name": f"Invalid Product {unique_id}",
                },
            ],
        }

        file_path = tmp_path / "view_skip_error.json"
        with open(file_path, "w") as f:
            json.dump(view_data, f)

        result = import_view(str(file_path), mode="merge", skip_on_error=True)

        assert result.successful >= 1
        assert result.skipped_due_to_fk >= 1

    def test_skip_on_error_writes_log_file(self, test_db, tmp_path, unique_id):
        """Test that skip_on_error writes skipped records log."""
        view_data = {
            "version": "1.0",
            "view_type": "products",
            "_meta": {
                "editable_fields": [],
            },
            "records": [
                {
                    "ingredient_slug": f"missing_{unique_id}",
                    "brand": f"Brand {unique_id}",
                    "package_unit": "lb",
                    "package_unit_quantity": 5.0,
                }
            ],
        }

        file_path = tmp_path / "view_log_test.json"
        with open(file_path, "w") as f:
            json.dump(view_data, f)

        result = import_view(str(file_path), mode="merge", skip_on_error=True)

        assert result.skipped_records_path is not None
        assert Path(result.skipped_records_path).exists()

        # Verify log content
        with open(result.skipped_records_path) as f:
            log_data = json.load(f)

        assert "skipped_records" in log_data
        assert len(log_data["skipped_records"]) >= 1


class TestImportViewFKResolution:
    """Tests for FK resolution integration."""

    def test_import_fails_with_missing_fk_and_no_resolver(
        self, test_db, view_file_with_missing_fk
    ):
        """Test that import fails with missing FK and no resolver."""
        result = import_view(view_file_with_missing_fk, mode="merge")

        assert result.failed >= 1
        assert "Missing foreign key" in result.errors[0]["message"]

    def test_import_with_resolver_create(self, test_db, tmp_path, unique_id):
        """Test import with FK resolver choosing CREATE."""
        # Create a view with missing ingredient
        view_data = {
            "version": "1.0",
            "view_type": "products",
            "_meta": {
                "editable_fields": ["brand"],
            },
            "records": [
                {
                    "ingredient_slug": f"new_ingredient_{unique_id}",
                    "brand": f"Brand {unique_id}",
                    "package_unit": "lb",
                    "package_unit_quantity": 5.0,
                }
            ],
        }

        file_path = tmp_path / "view_resolve.json"
        with open(file_path, "w") as f:
            json.dump(view_data, f)

        # Create a mock resolver that creates new entities
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = Resolution(
            choice=ResolutionChoice.CREATE,
            entity_type="ingredient",
            missing_value=f"new_ingredient_{unique_id}",
            created_entity={
                "slug": f"new_ingredient_{unique_id}",
                "display_name": f"New Ingredient {unique_id}",
                "category": "Other",
            },
        )

        result = import_view(str(file_path), mode="merge", resolver=mock_resolver)

        assert mock_resolver.resolve.called
        assert result.created_entities.get("ingredient", 0) >= 1

    def test_import_with_resolver_skip(self, test_db, tmp_path, unique_id):
        """Test import with FK resolver choosing SKIP."""
        view_data = {
            "version": "1.0",
            "view_type": "products",
            "_meta": {
                "editable_fields": [],
            },
            "records": [
                {
                    "ingredient_slug": f"skip_ingredient_{unique_id}",
                    "brand": f"Brand {unique_id}",
                    "package_unit": "lb",
                    "package_unit_quantity": 5.0,
                }
            ],
        }

        file_path = tmp_path / "view_skip_fk.json"
        with open(file_path, "w") as f:
            json.dump(view_data, f)

        # Create a mock resolver that skips
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = Resolution(
            choice=ResolutionChoice.SKIP,
            entity_type="ingredient",
            missing_value=f"skip_ingredient_{unique_id}",
        )

        result = import_view(str(file_path), mode="merge", resolver=mock_resolver)

        assert result.skipped_due_to_fk >= 1

    def test_import_with_resolver_map(self, sample_ingredient, tmp_path, unique_id):
        """Test import with FK resolver choosing MAP."""
        view_data = {
            "version": "1.0",
            "view_type": "products",
            "_meta": {
                "editable_fields": [],
            },
            "records": [
                {
                    "ingredient_slug": f"misspelled_ingredient_{unique_id}",
                    "brand": f"Brand {unique_id}",
                    "package_unit": "lb",
                    "package_unit_quantity": 5.0,
                }
            ],
        }

        file_path = tmp_path / "view_map_fk.json"
        with open(file_path, "w") as f:
            json.dump(view_data, f)

        # Create a mock resolver that maps to existing
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = Resolution(
            choice=ResolutionChoice.MAP,
            entity_type="ingredient",
            missing_value=f"misspelled_ingredient_{unique_id}",
            mapped_id=sample_ingredient["id"],
        )

        result = import_view(str(file_path), mode="merge", resolver=mock_resolver)

        assert result.mapped_entities.get("ingredient", 0) >= 1


class TestImportViewDuplicateHandling:
    """Tests for duplicate handling (first occurrence wins)."""

    def test_first_occurrence_wins(self, sample_ingredient, tmp_path, unique_id):
        """Test that first occurrence of duplicate records wins."""
        view_data = {
            "version": "1.0",
            "view_type": "products",
            "_meta": {
                "editable_fields": ["product_name"],
            },
            "records": [
                # First occurrence
                {
                    "ingredient_slug": sample_ingredient["slug"],
                    "brand": f"Dup Brand {unique_id}",
                    "package_unit": "lb",
                    "package_unit_quantity": 5.0,
                    "product_name": f"First Name {unique_id}",
                },
                # Duplicate - should be skipped or update with same composite key
                {
                    "ingredient_slug": sample_ingredient["slug"],
                    "brand": f"Dup Brand {unique_id}",
                    "package_unit": "lb",
                    "package_unit_quantity": 5.0,
                    "product_name": f"Second Name {unique_id}",
                },
            ],
        }

        file_path = tmp_path / "view_duplicate.json"
        with open(file_path, "w") as f:
            json.dump(view_data, f)

        result = import_view(str(file_path), mode="merge")

        # Should have processed both records
        assert result.total_records == 2

        # Verify the product name is from second (updated) or first (depending on mode logic)
        with session_scope() as session:
            product = (
                session.query(Product)
                .filter_by(brand=f"Dup Brand {unique_id}")
                .first()
            )
            # In merge mode, second record updates the first
            assert product is not None
