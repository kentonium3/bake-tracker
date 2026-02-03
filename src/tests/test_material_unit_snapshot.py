"""Tests for MaterialUnitSnapshot model and service functions."""

import pytest

from src.services.material_unit_service import (
    create_material_unit_snapshot,
    get_material_unit_snapshot,
    get_material_unit_snapshots_by_planning_id,
    create_unit,
    SnapshotCreationError,
)
from src.services.material_catalog_service import (
    create_category,
    create_subcategory,
    create_material,
    create_product,
)


@pytest.fixture
def db_session(test_db):
    """Provide a database session for tests."""
    return test_db()


@pytest.fixture
def sample_material(db_session):
    """Create a sample material hierarchy for testing."""
    category = create_category("Ribbons", session=db_session)
    subcategory = create_subcategory(category.id, "Satin", session=db_session)
    return create_material(subcategory.id, "Red Satin Ribbon", "linear_cm", session=db_session)


@pytest.fixture
def sample_product(db_session, sample_material):
    """Create a sample material product for testing."""
    return create_product(
        material_id=sample_material.id,
        name="Red Satin Roll",
        package_quantity=100,
        package_unit="cm",
        session=db_session,
    )


@pytest.fixture
def sample_material_unit(db_session, sample_product):
    """Create a sample MaterialUnit."""
    return create_unit(
        material_product_id=sample_product.id,
        name="6-inch Red Ribbon",
        quantity_per_unit=6.0,
        description="Cut ribbon segment",
        session=db_session,
    )


class TestCreateMaterialUnitSnapshot:
    """Tests for create_material_unit_snapshot()."""

    def test_creates_snapshot_with_denormalized_fields(
        self, db_session, sample_material_unit
    ):
        """Snapshot captures MaterialUnit fields and material details."""
        result = create_material_unit_snapshot(
            material_unit_id=sample_material_unit.id,
            session=db_session,
        )

        assert result["id"] is not None
        assert result["material_unit_id"] == sample_material_unit.id

        definition_data = result["definition_data"]
        assert definition_data["slug"] == sample_material_unit.slug
        assert definition_data["name"] == sample_material_unit.name
        assert definition_data["description"] == sample_material_unit.description
        assert definition_data["material_product_id"] == sample_material_unit.material_product_id
        assert definition_data["material_name"] == "Red Satin Ribbon"
        assert definition_data["material_category"] == "Ribbons"
        assert definition_data["quantity_per_unit"] == sample_material_unit.quantity_per_unit

    def test_raises_error_for_invalid_id(self, db_session):
        """Raises SnapshotCreationError for non-existent MaterialUnit."""
        with pytest.raises(SnapshotCreationError):
            create_material_unit_snapshot(material_unit_id=99999, session=db_session)


class TestGetMaterialUnitSnapshot:
    """Tests for get_material_unit_snapshot()."""

    def test_returns_snapshot_by_id(self, db_session, sample_material_unit):
        """Can retrieve snapshot by ID."""
        created = create_material_unit_snapshot(
            material_unit_id=sample_material_unit.id,
            session=db_session,
        )

        result = get_material_unit_snapshot(created["id"], session=db_session)

        assert result is not None
        assert result["id"] == created["id"]
        assert result["definition_data"]["slug"] == sample_material_unit.slug

    def test_returns_none_for_invalid_id(self, db_session):
        """Returns None for non-existent snapshot."""
        result = get_material_unit_snapshot(99999, session=db_session)
        assert result is None


class TestGetMaterialUnitSnapshotsByPlanningId:
    """Tests for get_material_unit_snapshots_by_planning_id()."""

    def test_returns_empty_list_when_no_matches(self, db_session):
        """Returns empty list when no snapshots exist for planning ID."""
        result = get_material_unit_snapshots_by_planning_id(123, session=db_session)
        assert result == []
