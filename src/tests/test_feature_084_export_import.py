"""
Tests for Feature 084 Export/Import Updates.

Tests MaterialUnit export with material_product_slug and Composition
handling of deprecated material_slug.
"""

import pytest

from src.services.material_catalog_service import (
    create_category,
    create_subcategory,
    create_material,
    create_product,
)
from src.services.import_export_service import (
    export_compositions_to_json,
    import_compositions_from_json,
)
from src.models import MaterialUnit, MaterialProduct, Material


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def db_session(test_db):
    """Provide a database session for tests."""
    return test_db()


@pytest.fixture
def sample_category(test_db):
    """Create a sample category for tests."""
    session = test_db()
    return create_category("Ribbons", session=session)


@pytest.fixture
def sample_subcategory(test_db, sample_category):
    """Create a sample subcategory for tests."""
    session = test_db()
    return create_subcategory(sample_category.id, "Satin", session=session)


@pytest.fixture
def sample_material(test_db, sample_subcategory):
    """Create a sample material (linear_cm type) for tests."""
    session = test_db()
    return create_material(
        sample_subcategory.id,
        "Red Satin Ribbon",
        "linear_cm",
        session=session,
    )


@pytest.fixture
def sample_each_material(test_db, sample_subcategory):
    """Create a sample material (each type) for tests."""
    session = test_db()
    return create_material(
        sample_subcategory.id,
        "Gift Box",
        "each",
        session=session,
    )


@pytest.fixture
def sample_material_product(test_db, sample_material):
    """Create a sample material product for tests."""
    session = test_db()
    return create_product(
        sample_material.id,
        "100ft Red Satin Roll",
        100,
        "feet",
        brand="Michaels",
        session=session,
    )


@pytest.fixture
def sample_material_unit(test_db, sample_material_product):
    """Create a sample material unit for tests."""
    session = test_db()
    unit = MaterialUnit(
        material_product_id=sample_material_product.id,
        name="10 ft Red Satin",
        slug="10-ft-red-satin",
        quantity_per_unit=10.0,
        description="10 foot cut",
    )
    session.add(unit)
    session.flush()
    return unit


@pytest.fixture
def sample_finished_good(test_db):
    """Create a sample finished good for tests."""
    from src.models import FinishedGood
    from src.models.assembly_type import AssemblyType

    session = test_db()
    fg = FinishedGood(
        display_name="Holiday Box",
        slug="holiday-box",
        assembly_type=AssemblyType.BUNDLE,
    )
    session.add(fg)
    session.flush()
    return fg


# ============================================================================
# MaterialUnit Export Tests (T027)
# ============================================================================


class TestMaterialUnitExport:
    """Tests for MaterialUnit export with material_product_slug."""

    def test_export_includes_material_product_slug(
        self, db_session, sample_material_unit, sample_material_product
    ):
        """MaterialUnit export should include material_product_slug."""
        from src.services.import_export_service import export_all_to_json
        import tempfile
        import json
        import os

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            result = export_all_to_json(filepath)
            assert result.success

            with open(filepath, 'r') as f:
                data = json.load(f)

            assert "material_units" in data
            assert len(data["material_units"]) >= 1

            unit_data = next(
                u for u in data["material_units"]
                if u["slug"] == "10-ft-red-satin"
            )
            assert "material_product_slug" in unit_data
            assert unit_data["material_product_slug"] == sample_material_product.slug
            # Ensure old format field is NOT present
            assert "material_slug" not in unit_data

        finally:
            os.unlink(filepath)

    def test_export_material_unit_includes_all_fields(
        self, db_session, sample_material_unit
    ):
        """MaterialUnit export should include all required fields."""
        from src.services.import_export_service import export_all_to_json
        import tempfile
        import json
        import os

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            result = export_all_to_json(filepath)
            assert result.success

            with open(filepath, 'r') as f:
                data = json.load(f)

            unit_data = next(
                u for u in data["material_units"]
                if u["slug"] == "10-ft-red-satin"
            )

            # Verify required fields
            assert unit_data["name"] == "10 ft Red Satin"
            assert unit_data["slug"] == "10-ft-red-satin"
            assert unit_data["quantity_per_unit"] == 10.0
            assert unit_data["description"] == "10 foot cut"

        finally:
            os.unlink(filepath)


# ============================================================================
# MaterialUnit Import Tests (T028)
# ============================================================================


class TestMaterialUnitImport:
    """Tests for MaterialUnit import with material_product_slug resolution."""

    def test_import_resolves_material_product_slug(
        self, db_session, sample_material_product
    ):
        """Import should resolve material_product_slug to material_product_id."""
        from src.services.catalog_import_service import import_material_units

        data = [
            {
                "material_product_slug": sample_material_product.slug,
                "name": "5 ft Cut",
                "slug": "5-ft-cut",
                "quantity_per_unit": 5.0,
            }
        ]

        result = import_material_units(data, mode="add", session=db_session)

        assert result.entity_counts["material_units"].added == 1
        unit = db_session.query(MaterialUnit).filter_by(slug="5-ft-cut").first()
        assert unit is not None
        assert unit.material_product_id == sample_material_product.id

    def test_import_invalid_product_slug_produces_error(self, db_session):
        """Import should error for invalid material_product_slug."""
        from src.services.catalog_import_service import import_material_units

        data = [
            {
                "material_product_slug": "nonexistent-product",
                "name": "Test Unit",
                "slug": "test-unit",
                "quantity_per_unit": 1.0,
            }
        ]

        result = import_material_units(data, mode="add", session=db_session)

        assert result.entity_counts["material_units"].failed == 1
        # Check error message mentions the missing product
        assert len(result.errors) == 1
        assert "nonexistent-product" in result.errors[0].message

    def test_import_old_format_material_slug_produces_error(
        self, db_session, sample_material
    ):
        """Import with old material_slug format should produce migration error."""
        from src.services.catalog_import_service import import_material_units

        data = [
            {
                "material_slug": sample_material.slug,  # Old format
                "name": "Test Unit",
                "slug": "test-unit",
                "quantity_per_unit": 1.0,
            }
        ]

        result = import_material_units(data, mode="add", session=db_session)

        assert result.entity_counts["material_units"].failed == 1
        # Check error mentions migration
        assert len(result.errors) == 1
        assert "material_product_slug" in result.errors[0].message.lower()


# ============================================================================
# Composition Export Tests (T029)
# ============================================================================


class TestCompositionExport:
    """Tests for Composition export without material_id."""

    def test_export_composition_excludes_material_slug(self, db_session):
        """Composition export should NOT include material_slug."""
        # Export and verify no material_slug field
        compositions = export_compositions_to_json()

        for comp in compositions:
            assert "material_slug" not in comp
            assert "material_id" not in comp

    def test_export_composition_includes_material_unit_slug(
        self, db_session, sample_finished_good, sample_material_unit
    ):
        """Composition export should include material_unit_slug when set."""
        from src.models import Composition

        # Create composition with material_unit
        comp = Composition(
            assembly_id=sample_finished_good.id,
            material_unit_id=sample_material_unit.id,
            component_quantity=2,
        )
        db_session.add(comp)
        db_session.flush()

        compositions = export_compositions_to_json()

        # Find the composition we just created
        exported_comp = next(
            (c for c in compositions if c.get("material_unit_slug") == sample_material_unit.slug),
            None
        )
        assert exported_comp is not None
        assert exported_comp["material_unit_slug"] == sample_material_unit.slug
        assert exported_comp["component_quantity"] == 2.0


# ============================================================================
# Composition Import Tests (T030)
# ============================================================================


class TestCompositionImportDeprecatedMaterialSlug:
    """Tests for Composition import handling deprecated material_slug."""

    def test_import_composition_skips_material_slug(
        self, db_session, sample_finished_good
    ):
        """Import should skip compositions with deprecated material_slug."""
        data = [
            {
                "finished_good_slug": sample_finished_good.slug,
                "material_slug": "some-old-material",  # Deprecated
                "component_quantity": 1,
            }
        ]

        result = import_compositions_from_json(data, db_session)

        # Should be skipped, not error
        assert result.skipped == 1
        assert result.failed == 0
        # Check skip message mentions deprecated (skips are stored in warnings)
        skip_warnings = [w for w in result.warnings if w.get("warning_type") == "skipped"]
        assert len(skip_warnings) == 1
        assert "deprecated" in skip_warnings[0]["message"].lower()

    def test_import_composition_with_material_unit_slug_succeeds(
        self, db_session, sample_finished_good, sample_material_unit
    ):
        """Import should succeed for compositions with material_unit_slug."""
        from src.models import Composition

        data = [
            {
                "finished_good_slug": sample_finished_good.slug,
                "material_unit_slug": sample_material_unit.slug,
                "component_quantity": 3,
            }
        ]

        result = import_compositions_from_json(data, db_session)

        assert result.successful == 1
        comp = (
            db_session.query(Composition)
            .filter_by(
                assembly_id=sample_finished_good.id,
                material_unit_id=sample_material_unit.id
            )
            .first()
        )
        assert comp is not None
        assert comp.component_quantity == 3


# ============================================================================
# Round-Trip Tests (T031)
# ============================================================================


class TestMaterialUnitRoundTrip:
    """Tests for export->import round-trip with material_product_slug."""

    def test_material_unit_roundtrip_preserves_relationships(
        self, db_session, sample_material_unit, sample_material_product
    ):
        """Export->Import should preserve MaterialUnit relationships."""
        from src.services.import_export_service import export_all_to_json
        from src.services.catalog_import_service import import_material_units
        import tempfile
        import json
        import os

        original_slug = sample_material_unit.slug
        original_product_id = sample_material_unit.material_product_id

        # Export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            export_all_to_json(filepath)

            with open(filepath, 'r') as f:
                data = json.load(f)

            # Clear and re-import
            db_session.query(MaterialUnit).delete()
            db_session.flush()

            # Verify cleared
            assert db_session.query(MaterialUnit).count() == 0

            # Re-import
            result = import_material_units(
                data["material_units"], mode="add", session=db_session
            )

            # Verify imported
            reimported = db_session.query(MaterialUnit).filter_by(slug=original_slug).first()
            assert reimported is not None
            assert reimported.material_product_id == original_product_id

        finally:
            os.unlink(filepath)
