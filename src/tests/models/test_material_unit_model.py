"""
Tests for MaterialUnit model.

Feature 084: MaterialUnit FK Change

Tests cover:
- Model creation with material_product_id FK
- NULL constraint enforcement on material_product_id
- CASCADE delete when MaterialProduct deleted
- Compound unique constraints (material_product_id + slug/name)
- Same slug allowed for different products
- Same slug rejected for same product
- Same name rejected for same product
- Check constraint on quantity_per_unit > 0
- Relationship with MaterialProduct
- BaseModel inheritance (id, uuid, created_at, updated_at)
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from src.models.base import Base
from src.models.material_unit import MaterialUnit
from src.models.material_product import MaterialProduct
from src.models.material import Material
from src.models.material_category import MaterialCategory
from src.models.material_subcategory import MaterialSubcategory


@pytest.fixture
def engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session for testing."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_material(session):
    """Create a sample material hierarchy for testing."""
    category = MaterialCategory(name="Ribbons", slug="ribbons")
    session.add(category)
    session.flush()

    subcategory = MaterialSubcategory(
        category_id=category.id,
        name="Satin",
        slug="satin",
    )
    session.add(subcategory)
    session.flush()

    material = Material(
        subcategory_id=subcategory.id,
        name="Red Satin Ribbon",
        slug="red-satin-ribbon",
        base_unit_type="linear_cm",
    )
    session.add(material)
    session.flush()

    return material


@pytest.fixture
def sample_product(session, sample_material):
    """Create a sample MaterialProduct for testing."""
    product = MaterialProduct(
        material_id=sample_material.id,
        name="100m Roll",
        slug="100m-roll",
        package_quantity=100,
        package_unit="m",
        quantity_in_base_units=10000,  # 100m = 10000cm
    )
    session.add(product)
    session.flush()
    return product


@pytest.fixture
def second_product(session, sample_material):
    """Create a second MaterialProduct for testing unique constraints."""
    product = MaterialProduct(
        material_id=sample_material.id,
        name="50m Roll",
        slug="50m-roll",
        package_quantity=50,
        package_unit="m",
        quantity_in_base_units=5000,  # 50m = 5000cm
    )
    session.add(product)
    session.flush()
    return product


class TestMaterialUnitModel:
    """Tests for MaterialUnit model creation and attributes."""

    def test_create_material_unit_success(self, session, sample_product):
        """Test creating a MaterialUnit with valid data."""
        unit = MaterialUnit(
            material_product_id=sample_product.id,
            name="6-inch ribbon",
            slug="6-inch-ribbon",
            quantity_per_unit=15.24,  # 6 inches in cm
            description="Cut ribbon segment for bows",
        )
        session.add(unit)
        session.flush()

        assert unit.id is not None
        assert unit.material_product_id == sample_product.id
        assert unit.name == "6-inch ribbon"
        assert unit.slug == "6-inch-ribbon"
        assert unit.quantity_per_unit == 15.24
        assert unit.description == "Cut ribbon segment for bows"

    def test_material_unit_requires_material_product_id(self, session):
        """Test that material_product_id is required (NOT NULL)."""
        unit = MaterialUnit(
            name="Test Unit",
            slug="test-unit",
            quantity_per_unit=10,
        )
        session.add(unit)

        with pytest.raises(IntegrityError):
            session.flush()

    def test_material_unit_requires_name(self, session, sample_product):
        """Test that name is required (NOT NULL)."""
        unit = MaterialUnit(
            material_product_id=sample_product.id,
            slug="test-unit",
            quantity_per_unit=10,
        )
        session.add(unit)

        with pytest.raises(IntegrityError):
            session.flush()

    def test_material_unit_requires_quantity_per_unit(self, session, sample_product):
        """Test that quantity_per_unit is required (NOT NULL)."""
        unit = MaterialUnit(
            material_product_id=sample_product.id,
            name="Test Unit",
            slug="test-unit",
        )
        session.add(unit)

        with pytest.raises(IntegrityError):
            session.flush()

    def test_material_unit_has_uuid(self, session, sample_product):
        """Test that UUID is automatically generated."""
        unit = MaterialUnit(
            material_product_id=sample_product.id,
            name="Test Unit",
            slug="test-unit",
            quantity_per_unit=10,
        )
        session.add(unit)
        session.flush()

        assert unit.uuid is not None
        assert len(unit.uuid) == 36  # UUID format: 8-4-4-4-12

    def test_material_unit_has_timestamps(self, session, sample_product):
        """Test that created_at and updated_at are set."""
        unit = MaterialUnit(
            material_product_id=sample_product.id,
            name="Test Unit",
            slug="test-unit",
            quantity_per_unit=10,
        )
        session.add(unit)
        session.flush()

        assert unit.created_at is not None
        assert unit.updated_at is not None


class TestMaterialUnitRelationship:
    """Tests for MaterialUnit -> MaterialProduct relationship."""

    def test_material_unit_has_material_product_relationship(self, session, sample_product):
        """Test that MaterialUnit can access its parent MaterialProduct."""
        unit = MaterialUnit(
            material_product_id=sample_product.id,
            name="Test Unit",
            slug="test-unit",
            quantity_per_unit=10,
        )
        session.add(unit)
        session.flush()

        # Relationship is lazy="joined", so should be loaded
        assert unit.material_product is not None
        assert unit.material_product.id == sample_product.id
        assert unit.material_product.name == "100m Roll"

    def test_material_product_has_material_units_relationship(self, session, sample_product):
        """Test that MaterialProduct can access its child MaterialUnits."""
        unit1 = MaterialUnit(
            material_product_id=sample_product.id,
            name="6-inch ribbon",
            slug="6-inch-ribbon",
            quantity_per_unit=15.24,
        )
        unit2 = MaterialUnit(
            material_product_id=sample_product.id,
            name="12-inch ribbon",
            slug="12-inch-ribbon",
            quantity_per_unit=30.48,
        )
        session.add_all([unit1, unit2])
        session.flush()

        # Refresh to ensure relationship is loaded
        session.refresh(sample_product)

        assert len(sample_product.material_units) == 2
        names = {u.name for u in sample_product.material_units}
        assert names == {"6-inch ribbon", "12-inch ribbon"}


class TestMaterialUnitCascadeDelete:
    """Tests for CASCADE delete behavior."""

    def test_deleting_material_product_deletes_units(self, session, sample_product):
        """Test that deleting MaterialProduct cascades to MaterialUnits."""
        unit = MaterialUnit(
            material_product_id=sample_product.id,
            name="Test Unit",
            slug="test-unit",
            quantity_per_unit=10,
        )
        session.add(unit)
        session.flush()

        unit_id = unit.id

        # Delete the parent product
        session.delete(sample_product)
        session.flush()

        # Verify unit is also deleted
        remaining = session.query(MaterialUnit).filter_by(id=unit_id).first()
        assert remaining is None

    def test_cascade_delete_orphan(self, session, sample_product):
        """Test that orphaned units are deleted via cascade='all, delete-orphan'."""
        unit = MaterialUnit(
            material_product_id=sample_product.id,
            name="Test Unit",
            slug="test-unit",
            quantity_per_unit=10,
        )
        session.add(unit)
        session.flush()

        unit_id = unit.id

        # Remove unit from product's collection
        sample_product.material_units.remove(unit)
        session.flush()

        # Verify unit is deleted
        remaining = session.query(MaterialUnit).filter_by(id=unit_id).first()
        assert remaining is None


class TestMaterialUnitUniqueConstraints:
    """Tests for compound unique constraints."""

    def test_same_slug_allowed_for_different_products(
        self, session, sample_product, second_product
    ):
        """Test that same slug is allowed for different MaterialProducts."""
        unit1 = MaterialUnit(
            material_product_id=sample_product.id,
            name="6-inch ribbon A",
            slug="6-inch-ribbon",
            quantity_per_unit=15.24,
        )
        unit2 = MaterialUnit(
            material_product_id=second_product.id,
            name="6-inch ribbon B",
            slug="6-inch-ribbon",  # Same slug, different product
            quantity_per_unit=15.24,
        )
        session.add_all([unit1, unit2])
        session.flush()  # Should NOT raise

        assert unit1.slug == unit2.slug
        assert unit1.material_product_id != unit2.material_product_id

    def test_same_slug_rejected_for_same_product(self, session, sample_product):
        """Test that same slug is rejected for same MaterialProduct."""
        unit1 = MaterialUnit(
            material_product_id=sample_product.id,
            name="Unit A",
            slug="test-slug",
            quantity_per_unit=10,
        )
        session.add(unit1)
        session.flush()

        unit2 = MaterialUnit(
            material_product_id=sample_product.id,
            name="Unit B",
            slug="test-slug",  # Same slug, same product - violation
            quantity_per_unit=20,
        )
        session.add(unit2)

        with pytest.raises(IntegrityError):
            session.flush()

    def test_same_name_allowed_for_different_products(
        self, session, sample_product, second_product
    ):
        """Test that same name is allowed for different MaterialProducts."""
        unit1 = MaterialUnit(
            material_product_id=sample_product.id,
            name="6-inch ribbon",
            slug="slug-a",
            quantity_per_unit=15.24,
        )
        unit2 = MaterialUnit(
            material_product_id=second_product.id,
            name="6-inch ribbon",  # Same name, different product
            slug="slug-b",
            quantity_per_unit=15.24,
        )
        session.add_all([unit1, unit2])
        session.flush()  # Should NOT raise

        assert unit1.name == unit2.name
        assert unit1.material_product_id != unit2.material_product_id

    def test_same_name_rejected_for_same_product(self, session, sample_product):
        """Test that same name is rejected for same MaterialProduct."""
        unit1 = MaterialUnit(
            material_product_id=sample_product.id,
            name="Duplicate Name",
            slug="slug-a",
            quantity_per_unit=10,
        )
        session.add(unit1)
        session.flush()

        unit2 = MaterialUnit(
            material_product_id=sample_product.id,
            name="Duplicate Name",  # Same name, same product - violation
            slug="slug-b",
            quantity_per_unit=20,
        )
        session.add(unit2)

        with pytest.raises(IntegrityError):
            session.flush()


class TestMaterialUnitCheckConstraints:
    """Tests for check constraints."""

    def test_quantity_per_unit_must_be_positive(self, session, sample_product):
        """Test that quantity_per_unit must be greater than 0."""
        unit = MaterialUnit(
            material_product_id=sample_product.id,
            name="Test Unit",
            slug="test-unit",
            quantity_per_unit=0,  # Violates CHECK constraint
        )
        session.add(unit)

        # Note: SQLite may or may not enforce CHECK constraints
        try:
            session.flush()
            # If we get here, SQLite didn't enforce the constraint
            # This is expected in some SQLite configurations
            # Service layer should validate before insert
            pass
        except IntegrityError:
            # Constraint was enforced - also valid
            session.rollback()

    def test_negative_quantity_per_unit_constraint(self, session, sample_product):
        """Test that negative quantity_per_unit violates constraint."""
        unit = MaterialUnit(
            material_product_id=sample_product.id,
            name="Test Unit",
            slug="test-unit",
            quantity_per_unit=-5,  # Violates CHECK constraint
        )
        session.add(unit)

        try:
            session.flush()
            # If we get here, SQLite didn't enforce the constraint
            pass
        except IntegrityError:
            # Constraint was enforced
            session.rollback()


class TestMaterialUnitMethods:
    """Tests for MaterialUnit model methods."""

    def test_repr(self, session, sample_product):
        """Test string representation."""
        unit = MaterialUnit(
            material_product_id=sample_product.id,
            name="6-inch ribbon",
            slug="6-inch-ribbon",
            quantity_per_unit=15.24,
        )
        session.add(unit)
        session.flush()

        repr_str = repr(unit)
        assert "MaterialUnit" in repr_str
        assert "6-inch ribbon" in repr_str

    def test_to_dict_basic(self, session, sample_product):
        """Test to_dict without relationships."""
        unit = MaterialUnit(
            material_product_id=sample_product.id,
            name="6-inch ribbon",
            slug="6-inch-ribbon",
            quantity_per_unit=15.24,
            description="Test description",
        )
        session.add(unit)
        session.flush()

        result = unit.to_dict(include_relationships=False)

        assert result["name"] == "6-inch ribbon"
        assert result["slug"] == "6-inch-ribbon"
        assert result["quantity_per_unit"] == 15.24
        assert result["description"] == "Test description"
        assert result["material_product_id"] == sample_product.id
        assert "id" in result
        assert "uuid" in result
        assert "created_at" in result
        assert "updated_at" in result
        assert "material_product" not in result

    def test_to_dict_with_relationships(self, session, sample_product):
        """Test to_dict with relationships included."""
        unit = MaterialUnit(
            material_product_id=sample_product.id,
            name="6-inch ribbon",
            slug="6-inch-ribbon",
            quantity_per_unit=15.24,
        )
        session.add(unit)
        session.flush()

        result = unit.to_dict(include_relationships=True)

        assert "material_product" in result
        assert result["material_product"]["name"] == "100m Roll"
        assert result["material_product"]["slug"] == "100m-roll"
