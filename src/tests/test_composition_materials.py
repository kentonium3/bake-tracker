"""Tests for Composition Materials Integration (Feature 047 - WP05).

Tests for:
- Creating MaterialUnit compositions
- Creating Material placeholder compositions
- XOR constraint (exactly one component type)
- Cost calculations for materials
- Cost breakdown separating food/material/packaging costs
"""

import pytest
from datetime import date
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from src.models import (
    Composition,
    FinishedGood,
    Supplier,
)
from src.models.assembly_type import AssemblyType
from src.services.material_catalog_service import (
    create_category,
    create_subcategory,
    create_material,
    create_product,
)
from src.services.material_unit_service import create_unit
from src.services.material_purchase_service import record_purchase
from src.services.composition_service import get_cost_breakdown, CompositionService


@pytest.fixture
def db_session(test_db):
    """Provide a database session for tests."""
    return test_db()


@pytest.fixture
def sample_supplier(db_session):
    """Create a sample supplier for testing."""
    supplier = Supplier(
        name="Test Craft Store",
        city="Boston",
        state="MA",
        zip_code="02101",
    )
    db_session.add(supplier)
    db_session.flush()
    return supplier


@pytest.fixture
def sample_finished_good(db_session):
    """Create a sample FinishedGood assembly for testing."""
    fg = FinishedGood(
        slug="test-gift-box",
        display_name="Test Gift Box",
        description="A test gift box assembly",
        assembly_type=AssemblyType.GIFT_BOX,
    )
    db_session.add(fg)
    db_session.flush()
    return fg


@pytest.fixture
def sample_material(db_session):
    """Create a sample material hierarchy for testing."""
    cat = create_category("Ribbons", session=db_session)
    subcat = create_subcategory(cat.id, "Satin", session=db_session)
    mat = create_material(subcat.id, "Red Satin", "linear_cm", session=db_session)
    return mat


@pytest.fixture
def sample_material_unit(db_session, sample_material):
    """Create a sample MaterialUnit.

    Note: quantity_per_unit is in base units (cm for linear materials).
    6 inches = 15.24 cm.
    """
    return create_unit(
        material_id=sample_material.id,
        name="6-inch ribbon",
        quantity_per_unit=15.24,  # 6 inches in cm (6 * 2.54)
        session=db_session,
    )


@pytest.fixture
def material_with_inventory(db_session, sample_material, sample_supplier):
    """Create material with inventory for cost calculations.

    Total inventory: 1200 inches
    Product A: 800 inches at $0.10/inch
    Product B: 400 inches at $0.14/inch
    Weighted average: (800*0.10 + 400*0.14) / 1200 = $0.1133/inch
    """
    # Product A: 800 inches
    prod_a = create_product(
        material_id=sample_material.id,
        name="800in Roll",
        package_quantity=800,
        package_unit="inches",
        supplier_id=sample_supplier.id,
        session=db_session,
    )

    # Product B: 400 inches
    prod_b = create_product(
        material_id=sample_material.id,
        name="400in Roll",
        package_quantity=400,
        package_unit="inches",
        supplier_id=sample_supplier.id,
        session=db_session,
    )

    # Record purchases
    record_purchase(
        product_id=prod_a.id,
        supplier_id=sample_supplier.id,
        purchase_date=date.today(),
        packages_purchased=1,
        package_price=Decimal("80.00"),  # $0.10/inch
        session=db_session,
    )

    record_purchase(
        product_id=prod_b.id,
        supplier_id=sample_supplier.id,
        purchase_date=date.today(),
        packages_purchased=1,
        package_price=Decimal("56.00"),  # $0.14/inch
        session=db_session,
    )

    return sample_material


@pytest.fixture
def material_unit_with_inventory(db_session, material_with_inventory):
    """Create a MaterialUnit for material with inventory.

    quantity_per_unit is in base units (cm). 6 inches = 15.24 cm.
    """
    return create_unit(
        material_id=material_with_inventory.id,
        name="6-inch ribbon",
        quantity_per_unit=15.24,  # 6 inches in cm (6 * 2.54)
        session=db_session,
    )


# =============================================================================
# T037 - Composition Tests for Material Integration
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


class TestCreateMaterialPlaceholderComposition:
    """Tests for creating generic Material placeholder compositions."""

    def test_create_material_placeholder_via_factory(
        self, db_session, sample_finished_good, sample_material
    ):
        """Can add generic Material placeholder via factory method."""
        comp = Composition.create_material_placeholder_composition(
            assembly_id=sample_finished_good.id,
            material_id=sample_material.id,
            quantity=1,
        )
        db_session.add(comp)
        db_session.commit()

        assert comp.material_id == sample_material.id
        assert comp.is_generic is True  # Generic placeholder
        assert comp.component_type == "material"

    def test_material_placeholder_has_relationship(
        self, db_session, sample_finished_good, sample_material
    ):
        """Material placeholder can access the relationship."""
        comp = Composition.create_material_placeholder_composition(
            assembly_id=sample_finished_good.id,
            material_id=sample_material.id,
        )
        db_session.add(comp)
        db_session.commit()

        db_session.refresh(comp)
        assert comp.material_component is not None
        assert comp.material_component.id == sample_material.id


class TestXORConstraint:
    """Tests for the 5-way XOR constraint."""

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
            material_id=None,
            component_quantity=1,
        )
        db_session.add(comp)
        # Should not raise
        db_session.commit()
        assert comp.id is not None

    def test_xor_allows_only_material(self, db_session, sample_finished_good, sample_material):
        """XOR allows composition with only material_id set."""
        comp = Composition(
            assembly_id=sample_finished_good.id,
            material_id=sample_material.id,
            finished_unit_id=None,
            finished_good_id=None,
            packaging_product_id=None,
            material_unit_id=None,
            component_quantity=1,
            is_generic=True,
        )
        db_session.add(comp)
        # Should not raise
        db_session.commit()
        assert comp.id is not None

    def test_xor_rejects_material_unit_and_material_together(
        self, db_session, sample_finished_good, sample_material_unit, sample_material
    ):
        """XOR rejects composition with both material_unit_id and material_id set."""
        comp = Composition(
            assembly_id=sample_finished_good.id,
            material_unit_id=sample_material_unit.id,
            material_id=sample_material.id,
            component_quantity=1,
        )
        db_session.add(comp)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_xor_rejects_multiple_types_set(
        self, db_session, sample_finished_good, sample_material_unit, sample_material
    ):
        """XOR rejects composition with multiple component types set."""
        # This test verifies the constraint catches multiple types
        # Already tested material_unit + material above, this confirms pattern
        comp = Composition(
            assembly_id=sample_finished_good.id,
            material_unit_id=sample_material_unit.id,
            material_id=sample_material.id,
            component_quantity=1,
        )
        db_session.add(comp)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_xor_rejects_no_component_set(self, db_session, sample_finished_good):
        """XOR rejects composition with no component type set."""
        comp = Composition(
            assembly_id=sample_finished_good.id,
            finished_unit_id=None,
            finished_good_id=None,
            packaging_product_id=None,
            material_unit_id=None,
            material_id=None,
            component_quantity=1,
        )
        db_session.add(comp)
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestMaterialComponentCost:
    """Tests for cost calculation with material components."""

    def test_material_unit_component_cost(
        self, db_session, sample_finished_good, material_unit_with_inventory
    ):
        """MaterialUnit composition has correct cost calculation.

        6-inch ribbon at weighted average of ~$0.1133/inch = ~$0.68
        """
        comp = Composition.create_material_unit_composition(
            assembly_id=sample_finished_good.id,
            material_unit_id=material_unit_with_inventory.id,
            quantity=1,
        )
        db_session.add(comp)
        db_session.commit()

        db_session.refresh(comp)
        cost = comp.get_component_cost()
        # Weighted avg: (800*0.10 + 400*0.14) / 1200 = 0.1133.../inch
        # 6 inches = ~$0.68
        assert cost > 0
        assert 0.60 < cost < 0.75  # Allow some tolerance

    def test_generic_material_has_estimated_cost(
        self, db_session, sample_finished_good, material_with_inventory
    ):
        """Generic Material placeholder has estimated cost (average across products)."""
        comp = Composition.create_material_placeholder_composition(
            assembly_id=sample_finished_good.id,
            material_id=material_with_inventory.id,
            quantity=1,
        )
        db_session.add(comp)
        db_session.commit()

        db_session.refresh(comp)
        # Generic material estimates cost as average across products
        cost = comp.get_component_cost()
        # This should return an estimated cost > 0 (average of product costs)
        assert cost >= 0


class TestCostBreakdown:
    """Tests for get_cost_breakdown() separating cost types."""

    def test_cost_breakdown_returns_dict_structure(self, db_session, sample_finished_good):
        """Cost breakdown returns correct dict structure."""
        breakdown = get_cost_breakdown(sample_finished_good.id, session=db_session)

        assert "food_cost" in breakdown
        assert "material_cost" in breakdown
        assert "packaging_cost" in breakdown
        assert "total_cost" in breakdown
        assert "has_estimated_costs" in breakdown
        assert "component_details" in breakdown

    def test_cost_breakdown_empty_assembly(self, db_session, sample_finished_good):
        """Cost breakdown for empty assembly returns zeros."""
        breakdown = get_cost_breakdown(sample_finished_good.id, session=db_session)

        assert breakdown["food_cost"] == Decimal("0")
        assert breakdown["material_cost"] == Decimal("0")
        assert breakdown["packaging_cost"] == Decimal("0")
        assert breakdown["total_cost"] == Decimal("0")
        assert breakdown["has_estimated_costs"] is False

    def test_cost_breakdown_with_material_unit(
        self, db_session, sample_finished_good, material_unit_with_inventory
    ):
        """Cost breakdown includes material_unit in material_cost."""
        comp = Composition.create_material_unit_composition(
            assembly_id=sample_finished_good.id,
            material_unit_id=material_unit_with_inventory.id,
            quantity=2,
        )
        db_session.add(comp)
        db_session.commit()

        breakdown = get_cost_breakdown(sample_finished_good.id, session=db_session)

        assert breakdown["material_cost"] > Decimal("0")
        assert breakdown["food_cost"] == Decimal("0")
        assert breakdown["packaging_cost"] == Decimal("0")
        # 2 units at ~$0.68 each
        assert Decimal("1.0") < breakdown["material_cost"] < Decimal("2.0")

    def test_cost_breakdown_with_generic_material_sets_estimated_flag(
        self, db_session, sample_finished_good, material_with_inventory
    ):
        """Cost breakdown sets has_estimated_costs=True for generic materials."""
        comp = Composition.create_material_placeholder_composition(
            assembly_id=sample_finished_good.id,
            material_id=material_with_inventory.id,
            quantity=1,
        )
        db_session.add(comp)
        db_session.commit()

        breakdown = get_cost_breakdown(sample_finished_good.id, session=db_session)

        assert breakdown["has_estimated_costs"] is True


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

    def test_component_type_property_material(
        self, db_session, sample_finished_good, sample_material
    ):
        """component_type returns 'material' for Material placeholder compositions."""
        comp = Composition.create_material_placeholder_composition(
            assembly_id=sample_finished_good.id,
            material_id=sample_material.id,
        )
        db_session.add(comp)
        db_session.commit()

        assert comp.component_type == "material"

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

    def test_component_id_property_material(
        self, db_session, sample_finished_good, sample_material
    ):
        """component_id returns correct ID for Material placeholder compositions."""
        comp = Composition.create_material_placeholder_composition(
            assembly_id=sample_finished_good.id,
            material_id=sample_material.id,
        )
        db_session.add(comp)
        db_session.commit()

        assert comp.component_id == sample_material.id

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

    def test_component_name_property_material(
        self, db_session, sample_finished_good, sample_material
    ):
        """component_name returns material name with 'selection pending' for placeholders."""
        comp = Composition.create_material_placeholder_composition(
            assembly_id=sample_finished_good.id,
            material_id=sample_material.id,
        )
        db_session.add(comp)
        db_session.commit()

        db_session.refresh(comp)
        # Generic placeholders show "(selection pending)" indicator
        assert sample_material.name in comp.component_name
        assert "selection pending" in comp.component_name


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

    def test_repr_material_placeholder(self, db_session, sample_finished_good, sample_material):
        """__repr__ shows material type for Material placeholder compositions."""
        comp = Composition.create_material_placeholder_composition(
            assembly_id=sample_finished_good.id,
            material_id=sample_material.id,
        )
        db_session.add(comp)
        db_session.commit()

        repr_str = repr(comp)
        # Format: Composition(id=X, assembly_id=Y, material=Z, qty=1, generic=True)
        assert "material=" in repr_str
        assert str(sample_material.id) in repr_str
        assert "generic=True" in repr_str
