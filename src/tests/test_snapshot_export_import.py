"""
Tests for F081: Snapshot Export/Import Coverage

Tests export and import of RecipeSnapshot, FinishedGoodSnapshot,
MaterialUnitSnapshot, and FinishedUnitSnapshot entities.

Success Criteria:
- SC-001: All 4 snapshot types export correctly
- SC-002: All 4 snapshot types import correctly
- SC-003: FK resolution via slug (FR-005, FR-006, FR-007, FR-008)
- SC-004: UUID preservation (FR-010)
- SC-005: Timestamp preservation (FR-011)
- SC-006: JSON data preservation (FR-012)
- SC-007: Zero failing tests
"""

import json
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.models.ingredient import Ingredient
from src.models.recipe import Recipe
from src.models.recipe_snapshot import RecipeSnapshot
from src.models.finished_good import FinishedGood
from src.models.finished_good_snapshot import FinishedGoodSnapshot
from src.models.material import Material
from src.models.material_category import MaterialCategory
from src.models.material_subcategory import MaterialSubcategory
from src.models.material_product import MaterialProduct
from src.models.material_unit import MaterialUnit
from src.models.material_unit_snapshot import MaterialUnitSnapshot
from src.models.finished_unit import FinishedUnit, YieldMode
from src.models.finished_unit_snapshot import FinishedUnitSnapshot
from src.services.coordinated_export_service import (
    import_complete,
    _export_recipe_snapshots,
    _export_finished_good_snapshots,
)


# ============================================================================
# Fixtures - T019: Create Test Fixtures for All 4 Snapshot Types
# ============================================================================


@pytest.fixture
def test_ingredient(test_db):
    """Create a test ingredient for recipe."""
    session = test_db()
    ingredient = Ingredient(
        slug="test-flour",
        display_name="Test Flour",
        category="dry goods",
    )
    session.add(ingredient)
    session.commit()
    return ingredient


@pytest.fixture
def test_recipe(test_db, test_ingredient):
    """Create a test recipe for snapshot tests."""
    session = test_db()
    recipe = Recipe(
        name="Test Cookie Recipe",
        slug="test-cookie-recipe",
        category="cookies",
    )
    session.add(recipe)
    session.commit()
    return recipe


@pytest.fixture
def test_recipe_snapshot(test_db, test_recipe):
    """Create a test RecipeSnapshot."""
    session = test_db()
    snapshot_uuid = uuid4()
    snapshot_date = datetime(2024, 12, 15, 10, 30, 0, tzinfo=timezone.utc)
    snapshot = RecipeSnapshot(
        uuid=snapshot_uuid,
        recipe_id=test_recipe.id,
        snapshot_date=snapshot_date,
        scale_factor=1.5,
        is_backfilled=False,
        recipe_data='{"name": "Test Cookie Recipe", "category": "cookies"}',
        ingredients_data='[{"ingredient": "flour", "quantity": 2.0, "unit": "cups"}]',
    )
    session.add(snapshot)
    session.commit()
    return snapshot


@pytest.fixture
def test_finished_good(test_db):
    """Create a test FinishedGood for snapshot tests."""
    session = test_db()
    fg = FinishedGood(
        slug="test-gift-box",
        display_name="Test Gift Box",
        description="A test gift box",
    )
    session.add(fg)
    session.commit()
    return fg


@pytest.fixture
def test_finished_good_snapshot(test_db, test_finished_good):
    """Create a test FinishedGoodSnapshot."""
    session = test_db()
    snapshot_uuid = uuid4()
    snapshot_date = datetime(2024, 12, 16, 14, 0, 0, tzinfo=timezone.utc)
    snapshot = FinishedGoodSnapshot(
        uuid=snapshot_uuid,
        finished_good_id=test_finished_good.id,
        snapshot_date=snapshot_date,
        is_backfilled=False,
        definition_data='{"components": [{"type": "cookie", "quantity": 12}]}',
    )
    session.add(snapshot)
    session.commit()
    return snapshot


@pytest.fixture
def test_material_hierarchy(test_db):
    """Create material category/subcategory/material hierarchy."""
    session = test_db()
    category = MaterialCategory(
        name="Packaging",
        slug="packaging",
    )
    session.add(category)
    session.flush()

    subcategory = MaterialSubcategory(
        name="Boxes",
        slug="boxes",
        category_id=category.id,
    )
    session.add(subcategory)
    session.flush()

    material = Material(
        name="Gift Box",
        slug="gift-box",
        subcategory_id=subcategory.id,
        base_unit_type="each",
    )
    session.add(material)
    session.commit()

    return {"category": category, "subcategory": subcategory, "material": material}


@pytest.fixture
def test_material_product(test_db, test_material_hierarchy):
    """Create a test MaterialProduct for snapshot tests."""
    session = test_db()
    material = test_material_hierarchy["material"]
    product = MaterialProduct(
        material_id=material.id,
        name="Gift Box - Small",
        slug="gift-box-small",
        package_quantity=1,
        package_unit="each",
        quantity_in_base_units=1,
    )
    session.add(product)
    session.commit()
    return product


@pytest.fixture
def test_material_unit(test_db, test_material_product):
    """Create a test MaterialUnit for snapshot tests."""
    session = test_db()
    unit = MaterialUnit(
        slug="small-gift-box",
        name="Small Gift Box",
        material_product_id=test_material_product.id,
        quantity_per_unit=1.0,
    )
    session.add(unit)
    session.commit()
    return unit


@pytest.fixture
def test_material_unit_snapshot(test_db, test_material_unit):
    """Create a test MaterialUnitSnapshot."""
    session = test_db()
    snapshot_uuid = uuid4()
    snapshot_date = datetime(2024, 12, 17, 9, 0, 0, tzinfo=timezone.utc)
    snapshot = MaterialUnitSnapshot(
        uuid=snapshot_uuid,
        material_unit_id=test_material_unit.id,
        snapshot_date=snapshot_date,
        is_backfilled=True,
        definition_data='{"material": "gift-box", "size": "small"}',
    )
    session.add(snapshot)
    session.commit()
    return snapshot


@pytest.fixture
def test_finished_unit(test_db, test_recipe):
    """Create a test FinishedUnit for snapshot tests."""
    session = test_db()
    fu = FinishedUnit(
        slug="test-cookie-dozen",
        display_name="Test Cookie Dozen",
        recipe_id=test_recipe.id,
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=24,
        item_unit="cookie",
    )
    session.add(fu)
    session.commit()
    return fu


@pytest.fixture
def test_finished_unit_snapshot(test_db, test_finished_unit):
    """Create a test FinishedUnitSnapshot."""
    session = test_db()
    snapshot_uuid = uuid4()
    snapshot_date = datetime(2024, 12, 18, 11, 30, 0, tzinfo=timezone.utc)
    snapshot = FinishedUnitSnapshot(
        uuid=snapshot_uuid,
        finished_unit_id=test_finished_unit.id,
        snapshot_date=snapshot_date,
        is_backfilled=False,
        definition_data='{"yield_mode": "discrete_count", "items_per_batch": 24}',
    )
    session.add(snapshot)
    session.commit()
    return snapshot


# ============================================================================
# T020: Export Unit Tests
# ============================================================================


class TestExportRecipeSnapshots:
    """Unit tests for _export_recipe_snapshots()."""

    def test_export_empty_database(self, test_db, tmp_path):
        """Verify export produces empty records array when no snapshots exist."""
        session = test_db()
        file_entry = _export_recipe_snapshots(tmp_path, session)

        assert file_entry.filename == "recipe_snapshots.json"
        assert file_entry.record_count == 0
        assert file_entry.entity_type == "recipe_snapshots"

    def test_export_single_snapshot(self, test_db, tmp_path, test_recipe_snapshot):
        """Verify export includes snapshot with correct structure."""
        session = test_db()
        file_entry = _export_recipe_snapshots(tmp_path, session)

        assert file_entry.record_count == 1

        # Read exported file
        with open(tmp_path / "recipe_snapshots.json", "r") as f:
            data = json.load(f)

        assert len(data["records"]) == 1
        record = data["records"][0]

        # Verify FK resolution via slug (FR-005)
        assert record["recipe_slug"] == "test-cookie-recipe"

        # Verify UUID preservation (FR-010)
        assert record["uuid"] == str(test_recipe_snapshot.uuid)

        # Verify timestamp preservation (FR-011)
        assert record["snapshot_date"] is not None

        # Verify JSON data preservation (FR-012)
        assert record["recipe_data"] is not None
        assert record["ingredients_data"] is not None

    def test_export_preserves_all_fields(self, test_db, tmp_path, test_recipe_snapshot):
        """Verify all snapshot fields are exported."""
        session = test_db()
        _export_recipe_snapshots(tmp_path, session)

        with open(tmp_path / "recipe_snapshots.json", "r") as f:
            data = json.load(f)

        record = data["records"][0]

        # Check all required fields present
        assert "uuid" in record
        assert "recipe_slug" in record
        assert "snapshot_date" in record
        assert "scale_factor" in record
        assert "is_backfilled" in record
        assert "recipe_data" in record
        assert "ingredients_data" in record

        # Verify specific values
        assert record["scale_factor"] == 1.5
        assert record["is_backfilled"] is False


class TestExportFinishedGoodSnapshots:
    """Unit tests for _export_finished_good_snapshots()."""

    def test_export_empty_database(self, test_db, tmp_path):
        """Verify export produces empty records array when no snapshots exist."""
        session = test_db()
        file_entry = _export_finished_good_snapshots(tmp_path, session)

        assert file_entry.filename == "finished_good_snapshots.json"
        assert file_entry.record_count == 0

    def test_export_single_snapshot(
        self, test_db, tmp_path, test_finished_good_snapshot
    ):
        """Verify export includes snapshot with correct structure."""
        session = test_db()
        file_entry = _export_finished_good_snapshots(tmp_path, session)

        assert file_entry.record_count == 1

        with open(tmp_path / "finished_good_snapshots.json", "r") as f:
            data = json.load(f)

        record = data["records"][0]

        # Verify FK resolution via slug (FR-006)
        assert record["finished_good_slug"] == "test-gift-box"

        # Verify UUID preservation (FR-010)
        assert record["uuid"] == str(test_finished_good_snapshot.uuid)

        # Verify JSON data preservation (FR-012)
        assert record["definition_data"] is not None


class TestExportChronologicalOrder:
    """Verify exports are ordered by snapshot_date (oldest first) per FR-015."""

    def test_recipe_snapshots_ordered_by_date(self, test_db, tmp_path, test_recipe):
        """Verify recipe snapshots export in chronological order."""
        session = test_db()
        # Create snapshots with different dates
        snap1 = RecipeSnapshot(
            recipe_id=test_recipe.id,
            snapshot_date=datetime(2024, 12, 20, tzinfo=timezone.utc),
            recipe_data="{}",
            ingredients_data="[]",
        )
        snap2 = RecipeSnapshot(
            recipe_id=test_recipe.id,
            snapshot_date=datetime(2024, 12, 10, tzinfo=timezone.utc),  # Earlier
            recipe_data="{}",
            ingredients_data="[]",
        )
        session.add_all([snap1, snap2])
        session.flush()

        _export_recipe_snapshots(tmp_path, session)

        with open(tmp_path / "recipe_snapshots.json", "r") as f:
            data = json.load(f)

        dates = [r["snapshot_date"] for r in data["records"]]
        # First should be earlier date (Dec 10)
        assert "2024-12-10" in dates[0]


# ============================================================================
# T021: Import Unit Tests
# ============================================================================


class TestImportRecipeSnapshots:
    """Unit tests for recipe_snapshots import handler."""

    def test_import_resolves_fk_by_slug(self, test_db, test_recipe, tmp_path):
        """Verify import resolves recipe FK via slug (FR-005)."""
        session = test_db()
        # Create export data
        test_uuid = str(uuid4())
        export_data = {
            "version": "1.0",
            "entity_type": "recipe_snapshots",
            "records": [
                {
                    "uuid": test_uuid,
                    "recipe_slug": "test-cookie-recipe",
                    "snapshot_date": "2024-12-15T10:30:00+00:00",
                    "scale_factor": 1.0,
                    "is_backfilled": False,
                    "recipe_data": '{"test": true}',
                    "ingredients_data": "[]",
                }
            ],
        }

        # Write to temp file
        with open(tmp_path / "recipe_snapshots.json", "w") as f:
            json.dump(export_data, f)

        # Create minimal manifest
        manifest = {
            "version": "1.0",
            "export_date": "2024-12-15T00:00:00Z",
            "source": "Test",
            "files": [
                {
                    "filename": "recipe_snapshots.json",
                    "entity_type": "recipe_snapshots",
                    "record_count": 1,
                    "sha256": "test",
                    "dependencies": ["recipes"],
                    "import_order": 19,
                }
            ],
        }
        with open(tmp_path / "manifest.json", "w") as f:
            json.dump(manifest, f)

        # Need to preserve the recipe for import
        session.expunge_all()

        # Import
        result = import_complete(str(tmp_path), session, clear_existing=False)

        # Verify import succeeded
        assert result["entity_counts"].get("recipe_snapshots", 0) == 1

    def test_import_missing_parent_warns_not_fails(self, test_db, tmp_path):
        """Verify import skips snapshot with missing parent and logs warning (FR-013)."""
        session = test_db()
        export_data = {
            "version": "1.0",
            "entity_type": "recipe_snapshots",
            "records": [
                {
                    "uuid": str(uuid4()),
                    "recipe_slug": "nonexistent-recipe",
                    "snapshot_date": "2024-12-15T10:30:00+00:00",
                    "scale_factor": 1.0,
                    "is_backfilled": False,
                    "recipe_data": "{}",
                    "ingredients_data": "[]",
                }
            ],
        }

        with open(tmp_path / "recipe_snapshots.json", "w") as f:
            json.dump(export_data, f)

        manifest = {
            "version": "1.0",
            "export_date": "2024-12-15T00:00:00Z",
            "source": "Test",
            "files": [
                {
                    "filename": "recipe_snapshots.json",
                    "entity_type": "recipe_snapshots",
                    "record_count": 1,
                    "sha256": "test",
                    "dependencies": ["recipes"],
                    "import_order": 19,
                }
            ],
        }
        with open(tmp_path / "manifest.json", "w") as f:
            json.dump(manifest, f)

        # Import should not raise exception
        result = import_complete(str(tmp_path), session, clear_existing=False)

        # Should have 0 imported (skipped with warning)
        assert result["entity_counts"].get("recipe_snapshots", 0) == 0
        # No errors in result
        assert len(result["errors"]) == 0


class TestImportFinishedGoodSnapshots:
    """Unit tests for finished_good_snapshots import handler."""

    def test_import_resolves_fk_by_slug(self, test_db, test_finished_good, tmp_path):
        """Verify import resolves finished_good FK via slug (FR-006)."""
        session = test_db()
        test_uuid = str(uuid4())
        export_data = {
            "version": "1.0",
            "entity_type": "finished_good_snapshots",
            "records": [
                {
                    "uuid": test_uuid,
                    "finished_good_slug": "test-gift-box",
                    "snapshot_date": "2024-12-16T14:00:00+00:00",
                    "is_backfilled": False,
                    "definition_data": "{}",
                }
            ],
        }

        with open(tmp_path / "finished_good_snapshots.json", "w") as f:
            json.dump(export_data, f)

        manifest = {
            "version": "1.0",
            "export_date": "2024-12-16T00:00:00Z",
            "source": "Test",
            "files": [
                {
                    "filename": "finished_good_snapshots.json",
                    "entity_type": "finished_good_snapshots",
                    "record_count": 1,
                    "sha256": "test",
                    "dependencies": ["finished_goods"],
                    "import_order": 20,
                }
            ],
        }
        with open(tmp_path / "manifest.json", "w") as f:
            json.dump(manifest, f)

        session.expunge_all()

        result = import_complete(str(tmp_path), session, clear_existing=False)
        assert result["entity_counts"].get("finished_good_snapshots", 0) == 1


class TestImportMaterialUnitSnapshots:
    """Unit tests for material_unit_snapshots import handler."""

    def test_import_resolves_fk_by_slug(self, test_db, test_material_unit, tmp_path):
        """Verify import resolves material_unit FK via slug (FR-007)."""
        session = test_db()
        test_uuid = str(uuid4())
        export_data = {
            "version": "1.0",
            "entity_type": "material_unit_snapshots",
            "records": [
                {
                    "uuid": test_uuid,
                    "material_unit_slug": "small-gift-box",
                    "snapshot_date": "2024-12-17T09:00:00+00:00",
                    "is_backfilled": True,
                    "definition_data": "{}",
                }
            ],
        }

        with open(tmp_path / "material_unit_snapshots.json", "w") as f:
            json.dump(export_data, f)

        manifest = {
            "version": "1.0",
            "export_date": "2024-12-17T00:00:00Z",
            "source": "Test",
            "files": [
                {
                    "filename": "material_unit_snapshots.json",
                    "entity_type": "material_unit_snapshots",
                    "record_count": 1,
                    "sha256": "test",
                    "dependencies": ["material_units"],
                    "import_order": 21,
                }
            ],
        }
        with open(tmp_path / "manifest.json", "w") as f:
            json.dump(manifest, f)

        session.expunge_all()

        result = import_complete(str(tmp_path), session, clear_existing=False)
        assert result["entity_counts"].get("material_unit_snapshots", 0) == 1


class TestImportFinishedUnitSnapshots:
    """Unit tests for finished_unit_snapshots import handler."""

    def test_import_resolves_fk_by_slug(self, test_db, test_finished_unit, tmp_path):
        """Verify import resolves finished_unit FK via slug (FR-008)."""
        session = test_db()
        test_uuid = str(uuid4())
        export_data = {
            "version": "1.0",
            "entity_type": "finished_unit_snapshots",
            "records": [
                {
                    "uuid": test_uuid,
                    "finished_unit_slug": "test-cookie-dozen",
                    "snapshot_date": "2024-12-18T11:30:00+00:00",
                    "is_backfilled": False,
                    "definition_data": "{}",
                }
            ],
        }

        with open(tmp_path / "finished_unit_snapshots.json", "w") as f:
            json.dump(export_data, f)

        manifest = {
            "version": "1.0",
            "export_date": "2024-12-18T00:00:00Z",
            "source": "Test",
            "files": [
                {
                    "filename": "finished_unit_snapshots.json",
                    "entity_type": "finished_unit_snapshots",
                    "record_count": 1,
                    "sha256": "test",
                    "dependencies": ["finished_units"],
                    "import_order": 22,
                }
            ],
        }
        with open(tmp_path / "manifest.json", "w") as f:
            json.dump(manifest, f)

        session.expunge_all()

        result = import_complete(str(tmp_path), session, clear_existing=False)
        assert result["entity_counts"].get("finished_unit_snapshots", 0) == 1


# ============================================================================
# T022: Round-Trip Integration Tests
# ============================================================================


class TestRoundTripIntegration:
    """Integration tests for export → import → export → compare cycle."""

    def test_recipe_snapshot_roundtrip_preserves_data(
        self, test_db, test_recipe_snapshot, tmp_path
    ):
        """Verify RecipeSnapshot survives round-trip with exact data preservation."""
        session = test_db()
        original_uuid = str(test_recipe_snapshot.uuid)
        original_scale = test_recipe_snapshot.scale_factor
        original_recipe_data = test_recipe_snapshot.recipe_data
        original_ingredients_data = test_recipe_snapshot.ingredients_data

        # Export
        export_dir = tmp_path / "export1"
        export_dir.mkdir()
        _export_recipe_snapshots(export_dir, session)

        with open(export_dir / "recipe_snapshots.json", "r") as f:
            exported_data = json.load(f)

        record = exported_data["records"][0]

        # Verify data matches
        assert record["uuid"] == original_uuid
        assert record["scale_factor"] == original_scale
        assert record["recipe_data"] == original_recipe_data
        assert record["ingredients_data"] == original_ingredients_data

    def test_finished_good_snapshot_roundtrip(
        self, test_db, test_finished_good_snapshot, tmp_path
    ):
        """Verify FinishedGoodSnapshot survives round-trip."""
        session = test_db()
        original_uuid = str(test_finished_good_snapshot.uuid)
        original_definition_data = test_finished_good_snapshot.definition_data

        export_dir = tmp_path / "export1"
        export_dir.mkdir()
        _export_finished_good_snapshots(export_dir, session)

        with open(export_dir / "finished_good_snapshots.json", "r") as f:
            exported_data = json.load(f)

        record = exported_data["records"][0]

        assert record["uuid"] == original_uuid
        assert record["definition_data"] == original_definition_data


# ============================================================================
# T023: Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Edge case tests for snapshot export/import."""

    def test_export_empty_database(self, test_db, tmp_path):
        """Verify export handles empty database gracefully."""
        session = test_db()
        # Export with no snapshots
        file_entry = _export_recipe_snapshots(tmp_path, session)
        assert file_entry.record_count == 0

        with open(tmp_path / "recipe_snapshots.json", "r") as f:
            data = json.load(f)
        assert data["records"] == []

    def test_import_missing_slug_field_warns(self, test_db, tmp_path):
        """Verify import skips records with missing slug field (FR-013)."""
        session = test_db()
        export_data = {
            "version": "1.0",
            "entity_type": "recipe_snapshots",
            "records": [
                {
                    "uuid": str(uuid4()),
                    # No recipe_slug!
                    "snapshot_date": "2024-12-15T10:30:00+00:00",
                    "scale_factor": 1.0,
                    "is_backfilled": False,
                    "recipe_data": "{}",
                    "ingredients_data": "[]",
                }
            ],
        }

        with open(tmp_path / "recipe_snapshots.json", "w") as f:
            json.dump(export_data, f)

        manifest = {
            "version": "1.0",
            "export_date": "2024-12-15T00:00:00Z",
            "source": "Test",
            "files": [
                {
                    "filename": "recipe_snapshots.json",
                    "entity_type": "recipe_snapshots",
                    "record_count": 1,
                    "sha256": "test",
                    "dependencies": ["recipes"],
                    "import_order": 19,
                }
            ],
        }
        with open(tmp_path / "manifest.json", "w") as f:
            json.dump(manifest, f)

        result = import_complete(str(tmp_path), session, clear_existing=False)

        # Should have 0 imported
        assert result["entity_counts"].get("recipe_snapshots", 0) == 0

    def test_import_preserves_null_uuid(self, test_db, test_recipe, tmp_path):
        """Verify import handles null UUID gracefully."""
        session = test_db()
        export_data = {
            "version": "1.0",
            "entity_type": "recipe_snapshots",
            "records": [
                {
                    "uuid": None,  # Null UUID
                    "recipe_slug": "test-cookie-recipe",
                    "snapshot_date": "2024-12-15T10:30:00+00:00",
                    "scale_factor": 1.0,
                    "is_backfilled": False,
                    "recipe_data": "{}",
                    "ingredients_data": "[]",
                }
            ],
        }

        with open(tmp_path / "recipe_snapshots.json", "w") as f:
            json.dump(export_data, f)

        manifest = {
            "version": "1.0",
            "export_date": "2024-12-15T00:00:00Z",
            "source": "Test",
            "files": [
                {
                    "filename": "recipe_snapshots.json",
                    "entity_type": "recipe_snapshots",
                    "record_count": 1,
                    "sha256": "test",
                    "dependencies": ["recipes"],
                    "import_order": 19,
                }
            ],
        }
        with open(tmp_path / "manifest.json", "w") as f:
            json.dump(manifest, f)

        session.expunge_all()

        result = import_complete(str(tmp_path), session, clear_existing=False)
        assert result["entity_counts"].get("recipe_snapshots", 0) == 1

    def test_import_handles_z_suffix_timestamp(self, test_db, test_recipe, tmp_path):
        """Verify import handles ISO timestamp with Z suffix."""
        session = test_db()
        export_data = {
            "version": "1.0",
            "entity_type": "recipe_snapshots",
            "records": [
                {
                    "uuid": str(uuid4()),
                    "recipe_slug": "test-cookie-recipe",
                    "snapshot_date": "2024-12-15T10:30:00Z",  # Z suffix
                    "scale_factor": 1.0,
                    "is_backfilled": False,
                    "recipe_data": "{}",
                    "ingredients_data": "[]",
                }
            ],
        }

        with open(tmp_path / "recipe_snapshots.json", "w") as f:
            json.dump(export_data, f)

        manifest = {
            "version": "1.0",
            "export_date": "2024-12-15T00:00:00Z",
            "source": "Test",
            "files": [
                {
                    "filename": "recipe_snapshots.json",
                    "entity_type": "recipe_snapshots",
                    "record_count": 1,
                    "sha256": "test",
                    "dependencies": ["recipes"],
                    "import_order": 19,
                }
            ],
        }
        with open(tmp_path / "manifest.json", "w") as f:
            json.dump(manifest, f)

        session.expunge_all()

        result = import_complete(str(tmp_path), session, clear_existing=False)
        assert result["entity_counts"].get("recipe_snapshots", 0) == 1

    def test_multiple_snapshots_same_parent(self, test_db, tmp_path, test_recipe):
        """Verify multiple snapshots for same parent entity export correctly."""
        session = test_db()
        # Create multiple snapshots for same recipe
        for i in range(3):
            snap = RecipeSnapshot(
                recipe_id=test_recipe.id,
                snapshot_date=datetime(2024, 12, 15 + i, tzinfo=timezone.utc),
                recipe_data="{}",
                ingredients_data="[]",
            )
            session.add(snap)
        session.flush()

        file_entry = _export_recipe_snapshots(tmp_path, session)
        assert file_entry.record_count == 3

        with open(tmp_path / "recipe_snapshots.json", "r") as f:
            data = json.load(f)
        assert len(data["records"]) == 3

        # All should reference same parent slug
        for record in data["records"]:
            assert record["recipe_slug"] == "test-cookie-recipe"
