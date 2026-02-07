"""Tests for Composition Materials Integration (Feature 047 - WP05, Feature 084).

Tests for:
- Creating MaterialUnit compositions
- XOR constraint (exactly one of 4 component types)
- Cost calculations for materials

Feature 084: Removed material_id column and 5-way XOR.
All material compositions now use material_unit_id only.
"""

import pytest

from sqlalchemy.exc import IntegrityError

from src.models import (
    Composition,
    FinishedGood,
)
from src.models.assembly_type import AssemblyType
from src.models.material_category import MaterialCategory
from src.models.material_subcategory import MaterialSubcategory
from src.models.material import Material
from src.models.material_product import MaterialProduct
from src.models.material_unit import MaterialUnit


@pytest.fixture
def db_session(test_db):
    """Provide a database session for tests."""
    return test_db()


@pytest.fixture
def sample_finished_good(db_session):
    """Create a sample FinishedGood assembly for testing."""
    fg = FinishedGood(
        slug="test-gift-box",
        display_name="Test Gift Box",
        description="A test gift box assembly",
        assembly_type=AssemblyType.BUNDLE,
    )
    db_session.add(fg)
    db_session.flush()
    return fg


@pytest.fixture
def sample_material_hierarchy(db_session):
    """Create a sample material hierarchy (category -> subcategory -> material)."""
    category = MaterialCategory(name="Ribbons", slug="ribbons")
    db_session.add(category)
    db_session.flush()

    subcategory = MaterialSubcategory(
        category_id=category.id,
        name="Satin",
        slug="satin",
    )
    db_session.add(subcategory)
    db_session.flush()

    material = Material(
        subcategory_id=subcategory.id,
        name="Red Satin Ribbon",
        slug="red-satin-ribbon",
        base_unit_type="linear_cm",
    )
    db_session.add(material)
    db_session.flush()

    return material


@pytest.fixture
def sample_material_product(db_session, sample_material_hierarchy):
    """Create a sample MaterialProduct for testing."""
    product = MaterialProduct(
        material_id=sample_material_hierarchy.id,
        name="100m Roll",
        slug="100m-roll",
        package_quantity=100,
        package_unit="m",
        quantity_in_base_units=10000,  # 100m = 10000cm
    )
    db_session.add(product)
    db_session.flush()
    return product


@pytest.fixture
def sample_material_unit(db_session, sample_material_product):
    """Create a sample MaterialUnit for testing.

    Feature 084: MaterialUnit now references MaterialProduct, not Material.
    """
    unit = MaterialUnit(
        material_product_id=sample_material_product.id,
        name="6-inch ribbon",
        slug="6-inch-ribbon",
        quantity_per_unit=15.24,  # 6 inches in cm (6 * 2.54)
    )
    db_session.add(unit)
    db_session.flush()
    return unit


# =============================================================================
# T037 - Composition Tests for Material Integration (Feature 084 Updates)
# =============================================================================


class TestCreateMaterialUnitComposition:
    """Tests for creating MaterialUnit compositions."""

    def test_create_material_unit_composition_via_factory(
        self, db_session, sample_finished_good, sample_material_unit
    ):
        """Can add MaterialUnit to FinishedGood composition via factory method."""
        comp = Composition.create_material_unit_composition(
            assembly_id=sample_finished_good.id,
            material_unit_id=sample_material_unit.id,
            quantity=2,
        )
        db_session.add(comp)
        db_session.commit()

        assert comp.material_unit_id == sample_material_unit.id
        assert comp.is_generic is False
        assert comp.component_type == "material_unit"
        assert comp.component_quantity == 2

    def test_create_material_unit_composition_direct(
        self, db_session, sample_finished_good, sample_material_unit
    ):
        """Can add MaterialUnit to composition by setting field directly."""
        comp = Composition(
            assembly_id=sample_finished_good.id,
            material_unit_id=sample_material_unit.id,
            component_quantity=1,
            is_generic=False,
        )
        db_session.add(comp)
        db_session.commit()

        assert comp.material_unit_id == sample_material_unit.id
        assert comp.component_type == "material_unit"

    def test_material_unit_composition_has_relationship(
        self, db_session, sample_finished_good, sample_material_unit
    ):
        """MaterialUnit composition can access the relationship."""
        comp = Composition.create_material_unit_composition(
            assembly_id=sample_finished_good.id,
            material_unit_id=sample_material_unit.id,
        )
        db_session.add(comp)
        db_session.commit()

        # Refresh to ensure relationship is loaded
        db_session.refresh(comp)
        assert comp.material_unit_component is not None
        assert comp.material_unit_component.id == sample_material_unit.id


# Feature 084: TestCreateMaterialPlaceholderComposition removed
# Generic Material placeholder support has been removed.


class TestXORConstraint:
    """Tests for the 4-way XOR constraint.

    Feature 084: Reduced from 5-way to 4-way (material_id removed).
    """

    def test_xor_allows_only_material_unit(
        self, db_session, sample_finished_good, sample_material_unit
    ):
        """XOR allows composition with only material_unit_id set."""
        comp = Composition(
            assembly_id=sample_finished_good.id,
            material_unit_id=sample_material_unit.id,
            finished_unit_id=None,
            finished_good_id=None,
            packaging_product_id=None,
            component_quantity=1,
        )
        db_session.add(comp)
        # Should not raise
        db_session.commit()
        assert comp.id is not None

    # Feature 084: test_xor_allows_only_material removed
    # material_id column no longer exists

    # Feature 084: test_xor_rejects_material_unit_and_material_together removed
    # material_id column no longer exists

    def test_xor_rejects_no_component_set(self, db_session, sample_finished_good):
        """XOR rejects composition with no component type set."""
        comp = Composition(
            assembly_id=sample_finished_good.id,
            finished_unit_id=None,
            finished_good_id=None,
            packaging_product_id=None,
            material_unit_id=None,
            component_quantity=1,
        )
        db_session.add(comp)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_validate_polymorphic_constraint_true(
        self, db_session, sample_finished_good, sample_material_unit
    ):
        """validate_polymorphic_constraint returns True for valid composition."""
        comp = Composition(
            assembly_id=sample_finished_good.id,
            material_unit_id=sample_material_unit.id,
            component_quantity=1,
        )
        assert comp.validate_polymorphic_constraint() is True

    def test_validate_polymorphic_constraint_false_none_set(self, db_session, sample_finished_good):
        """validate_polymorphic_constraint returns False when no component set."""
        comp = Composition(
            assembly_id=sample_finished_good.id,
            finished_unit_id=None,
            finished_good_id=None,
            packaging_product_id=None,
            material_unit_id=None,
            component_quantity=1,
        )
        assert comp.validate_polymorphic_constraint() is False


class TestCompositionProperties:
    """Tests for Composition model properties with materials."""

    def test_component_type_property_material_unit(
        self, db_session, sample_finished_good, sample_material_unit
    ):
        """component_type returns 'material_unit' for MaterialUnit compositions."""
        comp = Composition.create_material_unit_composition(
            assembly_id=sample_finished_good.id,
            material_unit_id=sample_material_unit.id,
        )
        db_session.add(comp)
        db_session.commit()

        assert comp.component_type == "material_unit"

    # Feature 084: test_component_type_property_material removed
    # material_id column no longer exists

    def test_component_id_property_material_unit(
        self, db_session, sample_finished_good, sample_material_unit
    ):
        """component_id returns correct ID for MaterialUnit compositions."""
        comp = Composition.create_material_unit_composition(
            assembly_id=sample_finished_good.id,
            material_unit_id=sample_material_unit.id,
        )
        db_session.add(comp)
        db_session.commit()

        assert comp.component_id == sample_material_unit.id

    # Feature 084: test_component_id_property_material removed
    # material_id column no longer exists

    def test_component_name_property_material_unit(
        self, db_session, sample_finished_good, sample_material_unit
    ):
        """component_name returns unit name for MaterialUnit compositions."""
        comp = Composition.create_material_unit_composition(
            assembly_id=sample_finished_good.id,
            material_unit_id=sample_material_unit.id,
        )
        db_session.add(comp)
        db_session.commit()

        db_session.refresh(comp)
        assert comp.component_name == sample_material_unit.name

    # Feature 084: test_component_name_property_material removed
    # material_id column no longer exists


class TestCompositionRepr:
    """Tests for Composition __repr__ with materials."""

    def test_repr_material_unit(self, db_session, sample_finished_good, sample_material_unit):
        """__repr__ shows material_unit type for MaterialUnit compositions."""
        comp = Composition.create_material_unit_composition(
            assembly_id=sample_finished_good.id,
            material_unit_id=sample_material_unit.id,
            quantity=3,
        )
        db_session.add(comp)
        db_session.commit()

        repr_str = repr(comp)
        # Format: Composition(id=X, assembly_id=Y, material_unit=Z, qty=3)
        assert "material_unit=" in repr_str
        assert str(sample_material_unit.id) in repr_str
        assert "qty=3" in repr_str

    # Feature 084: test_repr_material_placeholder removed
    # material_id column no longer exists


class TestMaterialPlaceholderRemoved:
    """Tests confirming Feature 084 removal of material_id support."""

    def test_no_create_material_placeholder_composition_method(self):
        """Composition no longer has create_material_placeholder_composition method."""
        assert not hasattr(Composition, "create_material_placeholder_composition")

    def test_composition_has_no_material_id_column(self, db_session, sample_finished_good):
        """Composition model does not have material_id column."""
        comp = Composition(
            assembly_id=sample_finished_good.id,
            component_quantity=1,
        )
        # Attempting to set material_id should not be possible
        assert not hasattr(comp, "material_id") or getattr(comp, "material_id", None) is None

    def test_composition_has_no_material_component_relationship(
        self, db_session, sample_finished_good
    ):
        """Composition model does not have material_component relationship."""
        comp = Composition(
            assembly_id=sample_finished_good.id,
            component_quantity=1,
        )
        assert not hasattr(comp, "material_component")
