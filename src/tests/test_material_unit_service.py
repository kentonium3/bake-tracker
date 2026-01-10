"""Tests for Material Unit Service.

Tests MaterialUnit CRUD operations, availability calculations, cost calculations,
and consumption preview for the Materials Management System (Feature 047).
"""

import pytest
from decimal import Decimal

from src.services.material_unit_service import (
    create_unit,
    get_unit,
    list_units,
    update_unit,
    delete_unit,
    get_available_inventory,
    get_current_cost,
    preview_consumption,
    MaterialUnitNotFoundError,
    MaterialNotFoundError,
)
from src.services.material_catalog_service import (
    create_category,
    create_subcategory,
    create_material,
    create_product,
)
from src.services.material_purchase_service import record_purchase
from src.services.exceptions import ValidationError
from src.models import Supplier


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
def sample_material(db_session):
    """Create a sample material hierarchy for testing."""
    cat = create_category("Ribbons", session=db_session)
    subcat = create_subcategory(cat.id, "Satin", session=db_session)
    mat = create_material(subcat.id, "Red Satin", "linear_inches", session=db_session)
    return mat


@pytest.fixture
def material_with_products(db_session, sample_material, sample_supplier):
    """Create material with two products totaling 1200 inches.

    Product A: 800 inches at $0.10/inch
    Product B: 400 inches at $0.14/inch
    """
    # Create products - each 100ft roll = 1200 inches
    prod_a = create_product(
        material_id=sample_material.id,
        name="100ft Roll A",
        package_quantity=100,
        package_unit="feet",
        supplier_id=sample_supplier.id,
        session=db_session,
    )

    prod_b = create_product(
        material_id=sample_material.id,
        name="100ft Roll B",
        package_quantity=100,
        package_unit="feet",
        supplier_id=sample_supplier.id,
        session=db_session,
    )

    # Record purchases to set inventory and cost
    # Product A: 800 inches at $0.10/inch = $80 per 1200 inches
    # We need to give it 800 inches: 800/1200 * 1 package...
    # Actually let's use smaller packages

    # Recreate with simpler packages for easier math
    db_session.delete(prod_a)
    db_session.delete(prod_b)
    db_session.flush()

    # Product A: 800 inches (package is 800 inches)
    prod_a = create_product(
        material_id=sample_material.id,
        name="800in Roll",
        package_quantity=800,
        package_unit="inches",
        supplier_id=sample_supplier.id,
        session=db_session,
    )

    # Product B: 400 inches (package is 400 inches)
    prod_b = create_product(
        material_id=sample_material.id,
        name="400in Roll",
        package_quantity=400,
        package_unit="inches",
        supplier_id=sample_supplier.id,
        session=db_session,
    )

    # Record purchases
    # Product A: 1 package of 800in at $80 = $0.10/inch
    from datetime import date
    record_purchase(
        product_id=prod_a.id,
        supplier_id=sample_supplier.id,
        purchase_date=date.today(),
        packages_purchased=1,
        package_price=Decimal("80.00"),
        session=db_session,
    )

    # Product B: 1 package of 400in at $56 = $0.14/inch
    record_purchase(
        product_id=prod_b.id,
        supplier_id=sample_supplier.id,
        purchase_date=date.today(),
        packages_purchased=1,
        package_price=Decimal("56.00"),
        session=db_session,
    )

    return sample_material


@pytest.fixture
def sample_unit(db_session, sample_material):
    """Create a sample MaterialUnit."""
    return create_unit(
        material_id=sample_material.id,
        name="6-inch ribbon",
        quantity_per_unit=6,
        session=db_session,
    )


class TestCreateUnit:
    """Tests for create_unit function."""

    def test_create_unit_basic(self, db_session, sample_material):
        """Create a basic MaterialUnit."""
        unit = create_unit(
            material_id=sample_material.id,
            name="6-inch ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        assert unit is not None
        assert unit.name == "6-inch ribbon"
        assert unit.quantity_per_unit == 6
        assert unit.slug == "6_inch_ribbon"
        assert unit.material_id == sample_material.id

    def test_create_unit_custom_slug(self, db_session, sample_material):
        """Create unit with custom slug."""
        unit = create_unit(
            material_id=sample_material.id,
            name="6-inch ribbon",
            quantity_per_unit=6,
            slug="six_inch",
            session=db_session,
        )

        assert unit.slug == "six_inch"

    def test_create_unit_duplicate_slug(self, db_session, sample_material):
        """Duplicate slug raises error."""
        create_unit(
            material_id=sample_material.id,
            name="Unit 1",
            quantity_per_unit=6,
            slug="test_slug",
            session=db_session,
        )

        with pytest.raises(ValidationError) as exc:
            create_unit(
                material_id=sample_material.id,
                name="Unit 2",
                quantity_per_unit=6,
                slug="test_slug",
                session=db_session,
            )
        assert "already exists" in str(exc.value)

    def test_create_unit_auto_slug_uniqueness(self, db_session, sample_material):
        """Auto-generated slugs are unique."""
        unit1 = create_unit(
            material_id=sample_material.id,
            name="Test Unit",
            quantity_per_unit=6,
            session=db_session,
        )
        unit2 = create_unit(
            material_id=sample_material.id,
            name="Test Unit",
            quantity_per_unit=6,
            session=db_session,
        )

        assert unit1.slug != unit2.slug
        assert unit1.slug == "test_unit"
        assert unit2.slug == "test_unit_1"

    def test_create_unit_invalid_material(self, db_session):
        """Invalid material_id raises error."""
        with pytest.raises(MaterialNotFoundError):
            create_unit(
                material_id=99999,
                name="Test",
                quantity_per_unit=6,
                session=db_session,
            )

    def test_create_unit_zero_quantity(self, db_session, sample_material):
        """Zero quantity_per_unit raises error."""
        with pytest.raises(ValidationError) as exc:
            create_unit(
                material_id=sample_material.id,
                name="Test",
                quantity_per_unit=0,
                session=db_session,
            )
        assert "positive" in str(exc.value)

    def test_create_unit_negative_quantity(self, db_session, sample_material):
        """Negative quantity_per_unit raises error."""
        with pytest.raises(ValidationError) as exc:
            create_unit(
                material_id=sample_material.id,
                name="Test",
                quantity_per_unit=-1,
                session=db_session,
            )
        assert "positive" in str(exc.value)

    def test_create_unit_empty_name(self, db_session, sample_material):
        """Empty name raises error."""
        with pytest.raises(ValidationError) as exc:
            create_unit(
                material_id=sample_material.id,
                name="",
                quantity_per_unit=6,
                session=db_session,
            )
        assert "empty" in str(exc.value)

    def test_create_unit_with_description(self, db_session, sample_material):
        """Create unit with description."""
        unit = create_unit(
            material_id=sample_material.id,
            name="Test",
            quantity_per_unit=6,
            description="Test description",
            session=db_session,
        )

        assert unit.description == "Test description"


class TestGetUnit:
    """Tests for get_unit function."""

    def test_get_unit_by_id(self, db_session, sample_unit):
        """Get unit by ID."""
        unit = get_unit(unit_id=sample_unit.id, session=db_session)
        assert unit.id == sample_unit.id

    def test_get_unit_by_slug(self, db_session, sample_unit):
        """Get unit by slug."""
        unit = get_unit(slug=sample_unit.slug, session=db_session)
        assert unit.slug == sample_unit.slug

    def test_get_unit_not_found(self, db_session):
        """Non-existent unit raises error."""
        with pytest.raises(MaterialUnitNotFoundError):
            get_unit(unit_id=99999, session=db_session)

    def test_get_unit_neither_param(self, db_session):
        """Neither unit_id nor slug raises error."""
        with pytest.raises(ValidationError):
            get_unit(session=db_session)


class TestListUnits:
    """Tests for list_units function."""

    def test_list_all_units(self, db_session, sample_material):
        """List all units."""
        create_unit(sample_material.id, "Unit 1", 6, session=db_session)
        create_unit(sample_material.id, "Unit 2", 12, session=db_session)

        units = list_units(session=db_session)
        assert len(units) == 2

    def test_list_units_by_material(self, db_session, sample_material):
        """List units filtered by material."""
        create_unit(sample_material.id, "Unit 1", 6, session=db_session)

        # Create another material with unit
        cat = create_category("Boxes", session=db_session)
        subcat = create_subcategory(cat.id, "Small", session=db_session)
        other_mat = create_material(subcat.id, "Gift Box", "each", session=db_session)
        create_unit(other_mat.id, "Single box", 1, session=db_session)

        ribbon_units = list_units(material_id=sample_material.id, session=db_session)
        assert len(ribbon_units) == 1
        assert ribbon_units[0].name == "Unit 1"


class TestUpdateUnit:
    """Tests for update_unit function."""

    def test_update_unit_name(self, db_session, sample_unit):
        """Update unit name."""
        updated = update_unit(
            unit_id=sample_unit.id,
            name="New Name",
            session=db_session,
        )
        assert updated.name == "New Name"

    def test_update_unit_description(self, db_session, sample_unit):
        """Update unit description."""
        updated = update_unit(
            unit_id=sample_unit.id,
            description="New description",
            session=db_session,
        )
        assert updated.description == "New description"

    def test_update_unit_not_found(self, db_session):
        """Update non-existent unit raises error."""
        with pytest.raises(MaterialUnitNotFoundError):
            update_unit(unit_id=99999, name="Test", session=db_session)

    def test_update_unit_empty_name(self, db_session, sample_unit):
        """Update with empty name raises error."""
        with pytest.raises(ValidationError) as exc:
            update_unit(unit_id=sample_unit.id, name="", session=db_session)
        assert "empty" in str(exc.value)


class TestDeleteUnit:
    """Tests for delete_unit function."""

    def test_delete_unit(self, db_session, sample_unit):
        """Delete a unit."""
        unit_id = sample_unit.id
        result = delete_unit(unit_id, session=db_session)

        assert result is True

        with pytest.raises(MaterialUnitNotFoundError):
            get_unit(unit_id=unit_id, session=db_session)

    def test_delete_unit_not_found(self, db_session):
        """Delete non-existent unit raises error."""
        with pytest.raises(MaterialUnitNotFoundError):
            delete_unit(99999, session=db_session)


class TestGetAvailableInventory:
    """Tests for get_available_inventory function."""

    def test_available_inventory_calculation(self, db_session, material_with_products):
        """Available inventory aggregates across products."""
        # Total inventory: 800 + 400 = 1200 inches
        unit = create_unit(
            material_id=material_with_products.id,
            name="6-inch ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        available = get_available_inventory(unit.id, session=db_session)
        # floor(1200 / 6) = 200
        assert available == 200

    def test_available_inventory_not_round(self, db_session, material_with_products):
        """Available inventory uses floor not round."""
        # Total inventory: 1200 inches
        unit = create_unit(
            material_id=material_with_products.id,
            name="7-inch ribbon",
            quantity_per_unit=7,
            session=db_session,
        )

        available = get_available_inventory(unit.id, session=db_session)
        # floor(1200 / 7) = floor(171.43) = 171
        assert available == 171

    def test_available_inventory_no_products(self, db_session, sample_material):
        """No products returns 0 inventory."""
        unit = create_unit(
            material_id=sample_material.id,
            name="6-inch ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        available = get_available_inventory(unit.id, session=db_session)
        assert available == 0

    def test_available_inventory_unit_not_found(self, db_session):
        """Non-existent unit raises error."""
        with pytest.raises(MaterialUnitNotFoundError):
            get_available_inventory(99999, session=db_session)


class TestGetCurrentCost:
    """Tests for get_current_cost function."""

    def test_current_cost_weighted_average(self, db_session, material_with_products):
        """Cost uses inventory-weighted average."""
        # Product A: 800 inches at $0.10/inch
        # Product B: 400 inches at $0.14/inch
        # Weighted avg = (800*0.10 + 400*0.14) / 1200 = (80 + 56) / 1200 = 0.1133...

        unit = create_unit(
            material_id=material_with_products.id,
            name="6-inch ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        cost = get_current_cost(unit.id, session=db_session)
        # Cost = 6 * 0.1133... = 0.68
        assert cost == Decimal("0.6800")

    def test_current_cost_no_products(self, db_session, sample_material):
        """No products returns 0 cost."""
        unit = create_unit(
            material_id=sample_material.id,
            name="6-inch ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        cost = get_current_cost(unit.id, session=db_session)
        assert cost == Decimal("0")

    def test_current_cost_unit_not_found(self, db_session):
        """Non-existent unit raises error."""
        with pytest.raises(MaterialUnitNotFoundError):
            get_current_cost(99999, session=db_session)


class TestPreviewConsumption:
    """Tests for preview_consumption function."""

    def test_preview_sufficient_inventory(self, db_session, material_with_products):
        """Preview with sufficient inventory."""
        unit = create_unit(
            material_id=material_with_products.id,
            name="6-inch ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        preview = preview_consumption(unit.id, quantity_needed=50, session=db_session)

        assert preview['can_fulfill'] is True
        assert preview['quantity_needed'] == 50
        assert preview['base_units_needed'] == 300  # 50 * 6
        assert preview['shortage_base_units'] == 0
        assert len(preview['allocations']) == 2  # Both products used

    def test_preview_insufficient_inventory(self, db_session, material_with_products):
        """Preview with insufficient inventory."""
        unit = create_unit(
            material_id=material_with_products.id,
            name="6-inch ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        # Try to consume more than available (200 units max)
        preview = preview_consumption(unit.id, quantity_needed=300, session=db_session)

        assert preview['can_fulfill'] is False
        assert preview['quantity_needed'] == 300
        assert preview['base_units_needed'] == 1800  # 300 * 6
        assert preview['shortage_base_units'] == 600  # 1800 - 1200

    def test_preview_proportional_allocation(self, db_session, material_with_products):
        """Allocations are proportional to inventory."""
        unit = create_unit(
            material_id=material_with_products.id,
            name="6-inch ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        preview = preview_consumption(unit.id, quantity_needed=100, session=db_session)

        # Total inventory: 1200 inches (800 A + 400 B)
        # Consuming 600 inches (100 * 6)
        # Product A (800/1200 = 66.7%) should get 400 inches
        # Product B (400/1200 = 33.3%) should get 200 inches

        allocations = {a['product_name']: a['base_units_consumed'] for a in preview['allocations']}
        assert allocations['800in Roll'] == 400.0  # 66.7% of 600
        assert allocations['400in Roll'] == 200.0  # 33.3% of 600

    def test_preview_no_inventory(self, db_session, sample_material):
        """Preview with no inventory."""
        unit = create_unit(
            material_id=sample_material.id,
            name="6-inch ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        preview = preview_consumption(unit.id, quantity_needed=10, session=db_session)

        assert preview['can_fulfill'] is False
        assert preview['available_base_units'] == 0
        assert len(preview['allocations']) == 0

    def test_preview_unit_not_found(self, db_session):
        """Non-existent unit raises error."""
        with pytest.raises(MaterialUnitNotFoundError):
            preview_consumption(99999, quantity_needed=10, session=db_session)

    def test_preview_includes_cost(self, db_session, material_with_products):
        """Preview includes cost calculation."""
        unit = create_unit(
            material_id=material_with_products.id,
            name="6-inch ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        preview = preview_consumption(unit.id, quantity_needed=50, session=db_session)

        # 50 units * 6 inches = 300 inches
        # Product A: 200 inches at $0.10 = $20
        # Product B: 100 inches at $0.14 = $14
        # Total = $34
        assert float(preview['total_cost']) == pytest.approx(34.0, rel=0.01)
