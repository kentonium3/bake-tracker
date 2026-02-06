"""Tests for Recipe Category Import/Export (Feature 096 - WP04).

Tests for:
- Exporting recipe categories in full backup JSON
- Exporting recipe categories in coordinated export
- Importing recipe categories with duplicate detection (UUID, slug)
- Round-trip data integrity (export -> clear -> import -> verify)
- Backward compatibility with old exports lacking recipe_categories
"""

import json
import pytest
import tempfile
from pathlib import Path

from src.models.recipe_category import RecipeCategory
from src.services.catalog_import_service import (
    import_recipe_categories,
    CatalogImportResult,
)
from src.services.import_export_service import (
    export_all_to_json,
    import_all_from_json_v4,
)
from src.services.coordinated_export_service import export_complete


@pytest.fixture
def db_session(test_db):
    """Provide a database session for tests."""
    return test_db()


@pytest.fixture
def sample_categories(db_session):
    """Create sample recipe categories for testing."""
    cats = []
    for name, slug, sort_order, desc in [
        ("Cakes", "cakes", 10, "Layer cakes, sheet cakes, bundt cakes"),
        ("Cookies", "cookies", 20, "Drop cookies, bar cookies, rolled cookies"),
        ("Candies", "candies", 30, None),
    ]:
        cat = RecipeCategory(
            name=name,
            slug=slug,
            sort_order=sort_order,
            description=desc,
        )
        db_session.add(cat)
        cats.append(cat)
    db_session.flush()
    return cats


# =============================================================================
# Export Tests (T018 - full backup, T019 - catalog export)
# =============================================================================


class TestRecipeCategoryExportFullBackup:
    """Tests for recipe category export in full backup JSON (T018)."""

    def test_export_includes_recipe_categories_key(self, db_session, sample_categories):
        """Full backup JSON includes recipe_categories array."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            result = export_all_to_json(f.name)

        assert result.success
        with open(f.name) as fh:
            data = json.load(fh)
        assert "recipe_categories" in data
        assert isinstance(data["recipe_categories"], list)

    def test_export_recipe_categories_data(self, db_session, sample_categories):
        """Full backup exports all recipe categories with correct fields."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            result = export_all_to_json(f.name)

        with open(f.name) as fh:
            data = json.load(fh)

        exported = data["recipe_categories"]
        assert len(exported) == 3

        # Verify fields are present
        cakes = next(c for c in exported if c["slug"] == "cakes")
        assert cakes["name"] == "Cakes"
        assert cakes["slug"] == "cakes"
        assert cakes["sort_order"] == 10
        assert cakes["description"] == "Layer cakes, sheet cakes, bundt cakes"
        assert cakes["uuid"] is not None

    def test_export_empty_when_no_categories(self, db_session):
        """Full backup exports empty array when no categories exist."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            result = export_all_to_json(f.name)

        with open(f.name) as fh:
            data = json.load(fh)

        assert data["recipe_categories"] == []

    def test_export_entity_count(self, db_session, sample_categories):
        """Export result includes recipe_categories count."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            result = export_all_to_json(f.name)

        assert result.entity_counts.get("recipe_categories") == 3

    def test_export_sorted_by_sort_order(self, db_session, sample_categories):
        """Exported recipe categories are sorted by sort_order."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_all_to_json(f.name)

        with open(f.name) as fh:
            data = json.load(fh)

        exported = data["recipe_categories"]
        sort_orders = [c["sort_order"] for c in exported]
        assert sort_orders == sorted(sort_orders)


class TestRecipeCategoryCatalogExport:
    """Tests for recipe category export in coordinated export (T019)."""

    def test_coordinated_export_includes_recipe_categories(
        self, db_session, sample_categories
    ):
        """Coordinated export includes recipe_categories.json file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir, session=db_session)

            filenames = [f.filename for f in manifest.files]
            assert "recipe_categories.json" in filenames

    def test_coordinated_export_file_content(self, db_session, sample_categories):
        """Coordinated export file contains correct data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_complete(tmpdir, session=db_session)

            with open(Path(tmpdir) / "recipe_categories.json") as f:
                data = json.load(f)

            assert len(data["records"]) == 3
            slugs = {r["slug"] for r in data["records"]}
            assert slugs == {"cakes", "cookies", "candies"}


# =============================================================================
# Import Tests (T020 - import_recipe_categories)
# =============================================================================


class TestRecipeCategoryImport:
    """Tests for import_recipe_categories() function (T020)."""

    def test_import_new_categories(self, db_session):
        """Import creates new recipe categories."""
        data = [
            {"name": "Pies", "slug": "pies", "sort_order": 40, "description": "Fruit pies"},
            {"name": "Breads", "slug": "breads", "sort_order": 50},
        ]

        result = import_recipe_categories(data, session=db_session)

        assert result.entity_counts["recipe_categories"].added == 2
        assert result.entity_counts["recipe_categories"].failed == 0

        # Verify in database
        pies = db_session.query(RecipeCategory).filter_by(slug="pies").first()
        assert pies is not None
        assert pies.name == "Pies"
        assert pies.sort_order == 40
        assert pies.description == "Fruit pies"

    def test_import_skips_existing_by_slug(self, db_session, sample_categories):
        """Import skips existing categories in ADD mode (slug match)."""
        data = [{"name": "Cakes", "slug": "cakes"}]

        result = import_recipe_categories(data, mode="add", session=db_session)

        assert result.entity_counts["recipe_categories"].skipped == 1
        assert result.entity_counts["recipe_categories"].added == 0

    def test_import_skips_existing_by_uuid(self, db_session, sample_categories):
        """Import skips existing categories when UUID matches."""
        existing_uuid = str(sample_categories[0].uuid)
        data = [{"name": "Renamed Cakes", "slug": "renamed-cakes", "uuid": existing_uuid}]

        result = import_recipe_categories(data, mode="add", session=db_session)

        assert result.entity_counts["recipe_categories"].skipped == 1
        assert result.entity_counts["recipe_categories"].added == 0

    def test_import_validates_missing_name(self, db_session):
        """Import fails when name is missing."""
        data = [{"slug": "no-name"}]

        result = import_recipe_categories(data, session=db_session)

        assert result.entity_counts["recipe_categories"].failed == 1
        assert any("name" in e.message.lower() for e in result.errors)

    def test_import_auto_generates_slug(self, db_session):
        """Import auto-generates slug from name when slug is missing."""
        data = [{"name": "Fruit Pies"}]

        result = import_recipe_categories(data, session=db_session)

        assert result.entity_counts["recipe_categories"].added == 1
        cat = db_session.query(RecipeCategory).filter_by(name="Fruit Pies").first()
        assert cat is not None
        assert cat.slug == "fruit-pies"

    def test_import_default_sort_order(self, db_session):
        """Import defaults sort_order to 0 when not provided."""
        data = [{"name": "Pastries", "slug": "pastries"}]

        result = import_recipe_categories(data, session=db_session)

        cat = db_session.query(RecipeCategory).filter_by(slug="pastries").first()
        assert cat.sort_order == 0

    def test_import_augment_fills_null_description(self, db_session, sample_categories):
        """AUGMENT mode fills null description on existing category."""
        # Candies has no description
        data = [{"name": "Candies", "slug": "candies", "description": "Fudge, toffee, etc."}]

        result = import_recipe_categories(data, mode="augment", session=db_session)

        assert result.entity_counts["recipe_categories"].augmented == 1
        candies = db_session.query(RecipeCategory).filter_by(slug="candies").first()
        assert candies.description == "Fudge, toffee, etc."

    def test_import_augment_skips_non_null_description(self, db_session, sample_categories):
        """AUGMENT mode skips when description already has value."""
        data = [{"name": "Cakes", "slug": "cakes", "description": "New description"}]

        result = import_recipe_categories(data, mode="augment", session=db_session)

        # Should skip because description already exists
        assert result.entity_counts["recipe_categories"].skipped == 1
        cakes = db_session.query(RecipeCategory).filter_by(slug="cakes").first()
        assert cakes.description == "Layer cakes, sheet cakes, bundt cakes"

    def test_import_empty_list(self, db_session):
        """Import handles empty data list gracefully."""
        result = import_recipe_categories([], session=db_session)

        assert result.entity_counts["recipe_categories"].added == 0
        assert result.entity_counts["recipe_categories"].failed == 0

    def test_import_preserves_uuid(self, db_session):
        """Import preserves UUID from export data when provided."""
        test_uuid = "12345678-1234-1234-1234-123456789abc"
        data = [{"name": "Tarts", "slug": "tarts", "uuid": test_uuid}]

        result = import_recipe_categories(data, session=db_session)

        assert result.entity_counts["recipe_categories"].added == 1
        cat = db_session.query(RecipeCategory).filter_by(slug="tarts").first()
        assert str(cat.uuid) == test_uuid


# =============================================================================
# Import Wiring Tests (T021)
# =============================================================================


class TestRecipeCategoryImportWiring:
    """Tests for recipe category import wiring in main import orchestration (T021)."""

    def test_unified_import_includes_recipe_categories(
        self, db_session, sample_categories
    ):
        """Unified import processes recipe_categories from JSON."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_all_to_json(f.name)

        # Clear categories
        db_session.query(RecipeCategory).delete()
        db_session.commit()

        # Re-import via unified import
        result = import_all_from_json_v4(f.name, mode="merge")

        assert result.entity_counts.get("recipe_category") is not None
        assert result.entity_counts["recipe_category"]["imported"] == 3

    def test_backward_compat_no_recipe_categories_key(self, db_session):
        """Old export files without recipe_categories import gracefully."""
        # Create a minimal export file without recipe_categories key
        export_data = {
            "version": "4.1",
            "exported_at": "2025-01-01T00:00:00Z",
            "application": "Bake Tracker",
            "ingredients": [],
            "products": [],
            "recipes": [],
        }
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as f:
            json.dump(export_data, f)

        # Should not raise
        result = import_all_from_json_v4(f.name, mode="merge")
        # No recipe_category key in result since it was not in the data
        assert "recipe_category" not in result.entity_counts


# =============================================================================
# Round-Trip Tests (T022)
# =============================================================================


class TestRecipeCategoryRoundtrip:
    """Tests for export -> import round-trip integrity (T022)."""

    def test_roundtrip_full_backup(self, db_session, sample_categories):
        """Full backup export -> clear -> import restores all categories."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_all_to_json(f.name)

        # Read exported data to verify before clearing
        with open(f.name) as fh:
            data = json.load(fh)
        assert len(data["recipe_categories"]) == 3

        # Clear categories
        db_session.query(RecipeCategory).delete()
        db_session.commit()
        assert db_session.query(RecipeCategory).count() == 0

        # Re-import
        result = import_all_from_json_v4(f.name, mode="merge")

        # Verify all restored
        assert db_session.query(RecipeCategory).count() == 3

        # Verify field values preserved
        cakes = db_session.query(RecipeCategory).filter_by(slug="cakes").first()
        assert cakes.name == "Cakes"
        assert cakes.sort_order == 10
        assert cakes.description == "Layer cakes, sheet cakes, bundt cakes"

        cookies = db_session.query(RecipeCategory).filter_by(slug="cookies").first()
        assert cookies.name == "Cookies"
        assert cookies.sort_order == 20

    def test_roundtrip_coordinated_export(self, db_session, sample_categories):
        """Coordinated export -> clear -> import restores categories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_complete(tmpdir, session=db_session)

            # Read exported data
            with open(Path(tmpdir) / "recipe_categories.json") as f:
                export_data = json.load(f)

            original_count = len(export_data["records"])
            assert original_count == 3

            # Clear and re-import
            db_session.query(RecipeCategory).delete()
            db_session.commit()

            result = import_recipe_categories(
                export_data["records"], session=db_session
            )

            assert result.entity_counts["recipe_categories"].added == original_count

            # Verify data preserved
            cakes = db_session.query(RecipeCategory).filter_by(slug="cakes").first()
            assert cakes is not None
            assert cakes.name == "Cakes"
            assert cakes.sort_order == 10

    def test_roundtrip_duplicate_import_skips_all(
        self, db_session, sample_categories
    ):
        """Re-importing the same data skips all (no duplicates created)."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_all_to_json(f.name)

        # Import again without clearing - all should be skipped
        result = import_all_from_json_v4(f.name, mode="merge")

        counts = result.entity_counts.get("recipe_category", {})
        assert counts.get("imported", 0) == 0
        assert counts.get("skipped", 0) == 3

        # Verify no duplicates
        assert db_session.query(RecipeCategory).count() == 3

    def test_roundtrip_preserves_null_description(self, db_session, sample_categories):
        """Round-trip preserves null description (Candies has no description)."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_all_to_json(f.name)

        db_session.query(RecipeCategory).delete()
        db_session.commit()

        import_all_from_json_v4(f.name, mode="merge")

        candies = db_session.query(RecipeCategory).filter_by(slug="candies").first()
        assert candies is not None
        assert candies.description is None
        assert candies.sort_order == 30
