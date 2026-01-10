"""Tests for Material Consumption Service (Feature 047 - WP06).

Tests for:
- Finding pending generic materials
- Validating material availability
- Recording material consumption with snapshots
- Inventory decrements
- Assembly blocking when insufficient inventory
"""

import pytest
from datetime import date
from decimal import Decimal

from src.models import (
    Composition,
    FinishedGood,
    AssemblyRun,
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
from src.services.material_consumption_service import (
    get_pending_materials,
    validate_material_availability,
    record_material_consumption,
    get_consumption_history,
    InsufficientMaterialError,
    MaterialAssignmentRequiredError,
)
from src.services.exceptions import ValidationError


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
def sample_assembly_run(db_session, sample_finished_good):
    """Create a sample AssemblyRun for testing."""
    run = AssemblyRun(
        finished_good_id=sample_finished_good.id,
        quantity_assembled=10,
        total_component_cost=Decimal("0"),
        per_unit_cost=Decimal("0"),
    )
    db_session.add(run)
    db_session.flush()
    return run


@pytest.fixture
def material_hierarchy(db_session):
    """Create a complete material hierarchy for testing."""
    cat = create_category("Ribbons", session=db_session)
    subcat = create_subcategory(cat.id, "Satin", session=db_session)
    mat = create_material(subcat.id, "Red Satin", "linear_inches", session=db_session)
    return {"category": cat, "subcategory": subcat, "material": mat}


@pytest.fixture
def material_with_products(db_session, material_hierarchy, sample_supplier):
    """Create material with two products and inventory.

    Product A: 800 inches at $0.10/inch
    Product B: 400 inches at $0.14/inch
    """
    material = material_hierarchy["material"]

    prod_a = create_product(
        material_id=material.id,
        name="800in Roll",
        package_quantity=800,
        package_unit="inches",
        supplier_id=sample_supplier.id,
        session=db_session,
    )

    prod_b = create_product(
        material_id=material.id,
        name="400in Roll",
        package_quantity=400,
        package_unit="inches",
        supplier_id=sample_supplier.id,
        session=db_session,
    )

    record_purchase(
        product_id=prod_a.id,
        supplier_id=sample_supplier.id,
        purchase_date=date.today(),
        packages_purchased=1,
        package_price=Decimal("80.00"),
        session=db_session,
    )

    record_purchase(
        product_id=prod_b.id,
        supplier_id=sample_supplier.id,
        purchase_date=date.today(),
        packages_purchased=1,
        package_price=Decimal("56.00"),
        session=db_session,
    )

    return {
        "material": material,
        "product_a": prod_a,
        "product_b": prod_b,
        "hierarchy": material_hierarchy,
    }


@pytest.fixture
def material_unit_with_inventory(db_session, material_with_products):
    """Create a MaterialUnit for material with inventory."""
    return create_unit(
        material_id=material_with_products["material"].id,
        name="6-inch ribbon",
        quantity_per_unit=6,
        session=db_session,
    )


@pytest.fixture
def fg_with_material_unit(db_session, sample_finished_good, material_unit_with_inventory):
    """Create FinishedGood with MaterialUnit composition."""
    comp = Composition.create_material_unit_composition(
        assembly_id=sample_finished_good.id,
        material_unit_id=material_unit_with_inventory.id,
        quantity=2,  # 2 units per assembly
    )
    db_session.add(comp)
    db_session.commit()
    return sample_finished_good


@pytest.fixture
def fg_with_generic_material(db_session, sample_finished_good, material_with_products):
    """Create FinishedGood with generic Material placeholder."""
    comp = Composition.create_material_placeholder_composition(
        assembly_id=sample_finished_good.id,
        material_id=material_with_products["material"].id,
        quantity=10,  # 10 base units per assembly
    )
    db_session.add(comp)
    db_session.commit()
    return {
        "finished_good": sample_finished_good,
        "composition": comp,
        "products": material_with_products,
    }


# =============================================================================
# Tests for get_pending_materials()
# =============================================================================


class TestGetPendingMaterials:
    """Tests for get_pending_materials function."""

    def test_returns_generic_materials_only(
        self, db_session, fg_with_generic_material
    ):
        """Returns list of materials needing resolution."""
        fg = fg_with_generic_material["finished_good"]
        pending = get_pending_materials(fg.id, session=db_session)

        assert len(pending) == 1
        assert pending[0]["material_name"] == "Red Satin"
        assert len(pending[0]["available_products"]) == 2

    def test_returns_empty_for_specific_materials(
        self, db_session, fg_with_material_unit
    ):
        """Returns empty list when only specific MaterialUnits used."""
        pending = get_pending_materials(fg_with_material_unit.id, session=db_session)
        assert len(pending) == 0

    def test_returns_product_details(
        self, db_session, fg_with_generic_material
    ):
        """Pending materials include product availability details."""
        fg = fg_with_generic_material["finished_good"]
        pending = get_pending_materials(fg.id, session=db_session)

        products = pending[0]["available_products"]
        assert any(p["name"] == "800in Roll" for p in products)
        assert any(p["name"] == "400in Roll" for p in products)


# =============================================================================
# Tests for validate_material_availability()
# =============================================================================


class TestValidateMaterialAvailability:
    """Tests for validate_material_availability function."""

    def test_passes_with_sufficient_inventory(
        self, db_session, fg_with_material_unit
    ):
        """Validation passes with sufficient inventory."""
        result = validate_material_availability(
            fg_with_material_unit.id,
            assembly_quantity=10,
            session=db_session,
        )

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_fails_with_insufficient_inventory(
        self, db_session, fg_with_material_unit
    ):
        """Validation fails when inventory insufficient."""
        result = validate_material_availability(
            fg_with_material_unit.id,
            assembly_quantity=9999,  # Way more than available
            session=db_session,
        )

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "insufficient inventory" in result["errors"][0].lower()

    def test_fails_without_assignment_for_generic(
        self, db_session, fg_with_generic_material
    ):
        """Validation fails when generic material has no assignment."""
        fg = fg_with_generic_material["finished_good"]

        result = validate_material_availability(
            fg.id,
            assembly_quantity=10,
            material_assignments=None,  # No assignments
            session=db_session,
        )

        assert result["valid"] is False
        assert "requires product assignment" in result["errors"][0]

    def test_passes_with_valid_assignment(
        self, db_session, fg_with_generic_material
    ):
        """Validation passes with valid product assignment."""
        fg = fg_with_generic_material["finished_good"]
        comp = fg_with_generic_material["composition"]
        product = fg_with_generic_material["products"]["product_a"]

        result = validate_material_availability(
            fg.id,
            assembly_quantity=10,
            material_assignments={comp.id: product.id},
            session=db_session,
        )

        assert result["valid"] is True


# =============================================================================
# Tests for record_material_consumption()
# =============================================================================


class TestRecordMaterialConsumption:
    """Tests for record_material_consumption function."""

    def test_creates_snapshot_records(
        self, db_session, sample_assembly_run, fg_with_material_unit, material_with_products
    ):
        """Consumption record includes snapshot fields."""
        consumptions = record_material_consumption(
            assembly_run_id=sample_assembly_run.id,
            finished_good_id=fg_with_material_unit.id,
            assembly_quantity=10,
            session=db_session,
        )

        assert len(consumptions) > 0
        c = consumptions[0]
        assert c.product_name is not None
        assert c.material_name is not None
        assert c.category_name is not None
        assert c.subcategory_name is not None

    def test_inventory_decrements(
        self, db_session, sample_assembly_run, fg_with_material_unit, material_with_products
    ):
        """Inventory decreases after consumption."""
        product_a = material_with_products["product_a"]
        original_inventory = product_a.current_inventory

        record_material_consumption(
            assembly_run_id=sample_assembly_run.id,
            finished_good_id=fg_with_material_unit.id,
            assembly_quantity=10,
            session=db_session,
        )

        db_session.refresh(product_a)
        assert product_a.current_inventory < original_inventory

    def test_raises_on_insufficient_inventory(
        self, db_session, sample_assembly_run, fg_with_material_unit
    ):
        """Raises ValidationError when inventory insufficient."""
        with pytest.raises(ValidationError) as exc_info:
            record_material_consumption(
                assembly_run_id=sample_assembly_run.id,
                finished_good_id=fg_with_material_unit.id,
                assembly_quantity=9999,
                session=db_session,
            )

        assert "insufficient inventory" in str(exc_info.value).lower()

    def test_generic_material_with_assignment(
        self, db_session, sample_assembly_run, fg_with_generic_material
    ):
        """Generic material consumption works with assignment."""
        fg = fg_with_generic_material["finished_good"]
        comp = fg_with_generic_material["composition"]
        product = fg_with_generic_material["products"]["product_a"]

        consumptions = record_material_consumption(
            assembly_run_id=sample_assembly_run.id,
            finished_good_id=fg.id,
            assembly_quantity=5,
            material_assignments={comp.id: product.id},
            session=db_session,
        )

        assert len(consumptions) == 1
        assert consumptions[0].product_name == product.display_name

    def test_generic_material_requires_assignment(
        self, db_session, sample_assembly_run, fg_with_generic_material
    ):
        """Generic material raises error without assignment."""
        fg = fg_with_generic_material["finished_good"]

        with pytest.raises(ValidationError):
            record_material_consumption(
                assembly_run_id=sample_assembly_run.id,
                finished_good_id=fg.id,
                assembly_quantity=5,
                material_assignments=None,
                session=db_session,
            )

    def test_calculates_cost_correctly(
        self, db_session, sample_assembly_run, fg_with_material_unit
    ):
        """Consumption records have correct cost calculations."""
        consumptions = record_material_consumption(
            assembly_run_id=sample_assembly_run.id,
            finished_good_id=fg_with_material_unit.id,
            assembly_quantity=10,
            session=db_session,
        )

        total_cost = sum(c.total_cost for c in consumptions)
        assert total_cost > 0

        # Verify cost = quantity * unit_cost
        for c in consumptions:
            expected = Decimal(str(c.quantity_consumed)) * c.unit_cost
            assert abs(c.total_cost - expected) < Decimal("0.01")


# =============================================================================
# Tests for get_consumption_history()
# =============================================================================


class TestGetConsumptionHistory:
    """Tests for get_consumption_history function."""

    def test_returns_snapshot_data(
        self, db_session, sample_assembly_run, fg_with_material_unit
    ):
        """History returns snapshot data, not current catalog."""
        record_material_consumption(
            assembly_run_id=sample_assembly_run.id,
            finished_good_id=fg_with_material_unit.id,
            assembly_quantity=10,
            session=db_session,
        )

        history = get_consumption_history(sample_assembly_run.id, session=db_session)

        assert len(history) > 0
        assert "product_name" in history[0]
        assert "material_name" in history[0]
        assert "category_name" in history[0]

    def test_returns_empty_for_no_consumptions(self, db_session, sample_assembly_run):
        """Returns empty list when no material consumptions."""
        history = get_consumption_history(sample_assembly_run.id, session=db_session)
        assert history == []


# =============================================================================
# Tests for Assembly Blocking
# =============================================================================


class TestAssemblyBlocking:
    """Tests for strict inventory blocking (no bypass)."""

    def test_no_bypass_option_for_insufficient_inventory(
        self, db_session, sample_assembly_run, fg_with_material_unit
    ):
        """Assembly is blocked with no bypass when inventory insufficient."""
        # This verifies the "no bypass" requirement from spec
        with pytest.raises(ValidationError) as exc_info:
            record_material_consumption(
                assembly_run_id=sample_assembly_run.id,
                finished_good_id=fg_with_material_unit.id,
                assembly_quantity=99999,
                session=db_session,
            )

        error_msg = str(exc_info.value)
        assert "insufficient" in error_msg.lower()
        # Verify there's no bypass functionality - error is raised and stops execution

    def test_atomic_operation_on_failure(
        self, db_session, sample_assembly_run, fg_with_material_unit, material_with_products
    ):
        """Failed consumption doesn't partially decrement inventory."""
        product_a = material_with_products["product_a"]
        original_inventory = product_a.current_inventory

        try:
            record_material_consumption(
                assembly_run_id=sample_assembly_run.id,
                finished_good_id=fg_with_material_unit.id,
                assembly_quantity=99999,
                session=db_session,
            )
        except ValidationError:
            pass

        # Inventory should be unchanged after failed attempt
        db_session.refresh(product_a)
        assert product_a.current_inventory == original_inventory
