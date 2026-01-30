"""Tests for Material Unit Service.

Tests MaterialUnit CRUD operations, availability calculations, cost calculations,
and consumption preview for the Materials Management System (Feature 047).

Feature 084: Updated to use material_product_id instead of material_id.
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
    MaterialProductNotFoundError,
    MaterialUnitInUseError,
)
from src.services.material_catalog_service import (
    create_category,
    create_subcategory,
    create_material,
    create_product,
)
from src.services.material_purchase_service import record_purchase
from src.services.exceptions import ValidationError
from src.models import Supplier, MaterialProduct, Composition, FinishedGood


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
    mat = create_material(subcat.id, "Red Satin", "linear_cm", session=db_session)
    return mat


@pytest.fixture
def sample_product(db_session, sample_material, sample_supplier):
    """Create a sample MaterialProduct for testing.

    Feature 084: MaterialUnits now belong to MaterialProduct, not Material.
    """
    product = create_product(
        material_id=sample_material.id,
        name="Red Satin 100cm Roll",
        package_quantity=100,
        package_unit="cm",
        supplier_id=sample_supplier.id,
        session=db_session,
    )
    return product


@pytest.fixture
def second_product(db_session, sample_material, sample_supplier):
    """Create a second MaterialProduct for testing cross-product uniqueness.

    Feature 084: Same name/slug allowed for different products.
    """
    product = create_product(
        material_id=sample_material.id,
        name="Red Satin 200cm Roll",
        package_quantity=200,
        package_unit="cm",
        supplier_id=sample_supplier.id,
        session=db_session,
    )
    return product


@pytest.fixture
def product_with_inventory(db_session, sample_product, sample_supplier):
    """Create a MaterialProduct with 1000 cm inventory at $0.10/cm.

    Feature 084: Inventory calculations now use single product.
    """
    from datetime import date

    record_purchase(
        product_id=sample_product.id,
        supplier_id=sample_supplier.id,
        purchase_date=date.today(),
        packages_purchased=10,  # 10 * 100cm = 1000cm
        package_price=Decimal("10.00"),  # $10 per 100cm = $0.10/cm
        session=db_session,
    )
    return sample_product


@pytest.fixture
def sample_unit(db_session, sample_product):
    """Create a sample MaterialUnit.

    Feature 084: Uses material_product_id instead of material_id.
    """
    return create_unit(
        material_product_id=sample_product.id,
        name="6-inch ribbon",
        quantity_per_unit=6,
        session=db_session,
    )


class TestCreateUnit:
    """Tests for create_unit function."""

    def test_create_unit_basic(self, db_session, sample_product):
        """Create a basic MaterialUnit.

        Feature 084: Uses material_product_id, slug uses hyphen style.
        """
        unit = create_unit(
            material_product_id=sample_product.id,
            name="6-inch ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        assert unit is not None
        assert unit.name == "6-inch ribbon"
        assert unit.quantity_per_unit == 6
        assert unit.slug == "6-inch-ribbon"  # Feature 084: hyphen style
        assert unit.material_product_id == sample_product.id

    def test_create_unit_custom_slug(self, db_session, sample_product):
        """Create unit with custom slug."""
        unit = create_unit(
            material_product_id=sample_product.id,
            name="6-inch ribbon",
            quantity_per_unit=6,
            slug="six-inch",
            session=db_session,
        )

        assert unit.slug == "six-inch"

    def test_create_unit_duplicate_slug(self, db_session, sample_product):
        """Duplicate slug within same product raises error."""
        create_unit(
            material_product_id=sample_product.id,
            name="Unit 1",
            quantity_per_unit=6,
            slug="test-slug",
            session=db_session,
        )

        with pytest.raises(ValidationError) as exc:
            create_unit(
                material_product_id=sample_product.id,
                name="Unit 2",
                quantity_per_unit=6,
                slug="test-slug",
                session=db_session,
            )
        assert "already exists" in str(exc.value)

    def test_create_unit_same_slug_different_product(
        self, db_session, sample_product, second_product
    ):
        """Same slug allowed for different products.

        Feature 084: Slug uniqueness is scoped to product.
        """
        unit1 = create_unit(
            material_product_id=sample_product.id,
            name="Test Unit",
            quantity_per_unit=6,
            slug="test-slug",
            session=db_session,
        )
        # Should not raise - different product
        unit2 = create_unit(
            material_product_id=second_product.id,
            name="Test Unit",
            quantity_per_unit=6,
            slug="test-slug",
            session=db_session,
        )

        assert unit1.slug == "test-slug"
        assert unit2.slug == "test-slug"
        assert unit1.material_product_id != unit2.material_product_id

    def test_create_unit_auto_slug_uniqueness(self, db_session, sample_product):
        """Auto-generated slugs are unique within product.

        Feature 084: Collision adds numeric suffix with hyphen.
        """
        # Create first unit with auto-generated slug
        unit1 = create_unit(
            material_product_id=sample_product.id,
            name="Test Unit",
            quantity_per_unit=6,
            session=db_session,
        )
        assert unit1.slug == "test-unit"

        # Create second unit with name that normalizes to same base slug
        # This should get auto-generated suffix for collision avoidance
        unit2 = create_unit(
            material_product_id=sample_product.id,
            name="Test-Unit!",  # Normalizes to "test-unit", but taken by unit1
            quantity_per_unit=6,
            session=db_session,
        )
        assert unit2.slug == "test-unit-2"  # Feature 084: hyphen suffix

    def test_create_unit_invalid_product(self, db_session):
        """Invalid material_product_id raises error.

        Feature 084: Changed from MaterialNotFoundError to MaterialProductNotFoundError.
        """
        with pytest.raises(MaterialProductNotFoundError):
            create_unit(
                material_product_id=99999,
                name="Test",
                quantity_per_unit=6,
                session=db_session,
            )

    def test_create_unit_zero_quantity(self, db_session, sample_product):
        """Zero quantity_per_unit raises error."""
        with pytest.raises(ValidationError) as exc:
            create_unit(
                material_product_id=sample_product.id,
                name="Test",
                quantity_per_unit=0,
                session=db_session,
            )
        assert "positive" in str(exc.value)

    def test_create_unit_negative_quantity(self, db_session, sample_product):
        """Negative quantity_per_unit raises error."""
        with pytest.raises(ValidationError) as exc:
            create_unit(
                material_product_id=sample_product.id,
                name="Test",
                quantity_per_unit=-1,
                session=db_session,
            )
        assert "positive" in str(exc.value)

    def test_create_unit_empty_name(self, db_session, sample_product):
        """Empty name raises error."""
        with pytest.raises(ValidationError) as exc:
            create_unit(
                material_product_id=sample_product.id,
                name="",
                quantity_per_unit=6,
                session=db_session,
            )
        assert "empty" in str(exc.value)

    def test_create_unit_with_description(self, db_session, sample_product):
        """Create unit with description."""
        unit = create_unit(
            material_product_id=sample_product.id,
            name="Test",
            quantity_per_unit=6,
            description="Test description",
            session=db_session,
        )

        assert unit.description == "Test description"

    def test_create_unit_duplicate_name(self, db_session, sample_product):
        """Duplicate name within same product raises error.

        Feature 084: Name uniqueness enforced per product.
        """
        create_unit(
            material_product_id=sample_product.id,
            name="Test Unit",
            quantity_per_unit=6,
            session=db_session,
        )

        with pytest.raises(ValidationError) as exc:
            create_unit(
                material_product_id=sample_product.id,
                name="Test Unit",
                quantity_per_unit=12,
                session=db_session,
            )
        assert "already exists" in str(exc.value)

    def test_create_unit_same_name_different_product(
        self, db_session, sample_product, second_product
    ):
        """Same name allowed for different products.

        Feature 084: Name uniqueness is scoped to product.
        """
        unit1 = create_unit(
            material_product_id=sample_product.id,
            name="Test Unit",
            quantity_per_unit=6,
            session=db_session,
        )
        # Should not raise - different product
        unit2 = create_unit(
            material_product_id=second_product.id,
            name="Test Unit",
            quantity_per_unit=6,
            session=db_session,
        )

        assert unit1.name == "Test Unit"
        assert unit2.name == "Test Unit"
        assert unit1.material_product_id != unit2.material_product_id


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

    def test_list_all_units(self, db_session, sample_product):
        """List all units."""
        create_unit(sample_product.id, "Unit 1", 6, session=db_session)
        create_unit(sample_product.id, "Unit 2", 12, session=db_session)

        units = list_units(session=db_session)
        assert len(units) == 2

    def test_list_units_by_product(self, db_session, sample_product, second_product):
        """List units filtered by product.

        Feature 084: Changed from material_id filter to material_product_id.
        """
        create_unit(sample_product.id, "Unit 1", 6, session=db_session)
        create_unit(second_product.id, "Unit 2", 12, session=db_session)

        product_units = list_units(material_product_id=sample_product.id, session=db_session)
        assert len(product_units) == 1
        assert product_units[0].name == "Unit 1"


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

    def test_update_unit_duplicate_name(self, db_session, sample_product):
        """Update to duplicate name within product raises error.

        Feature 084: Name uniqueness enforced per product on update.
        """
        create_unit(sample_product.id, "Unit 1", 6, session=db_session)
        unit2 = create_unit(sample_product.id, "Unit 2", 12, session=db_session)

        with pytest.raises(ValidationError) as exc:
            update_unit(unit_id=unit2.id, name="Unit 1", session=db_session)
        assert "already exists" in str(exc.value)

    def test_update_unit_same_name_no_change(self, db_session, sample_unit):
        """Update with same name (no change) succeeds."""
        updated = update_unit(
            unit_id=sample_unit.id,
            name=sample_unit.name,
            session=db_session,
        )
        assert updated.name == sample_unit.name


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

    def test_delete_unit_referenced_by_composition(self, db_session, sample_unit):
        """Delete unit referenced by Composition raises error.

        Feature 084: Deletion blocked if unit is used in compositions.
        """
        # Create a FinishedGood to act as assembly parent
        fg = FinishedGood(
            display_name="Test FG",
            slug="test-fg",
        )
        db_session.add(fg)
        db_session.flush()

        # Create Composition referencing the MaterialUnit
        comp = Composition(
            assembly_id=fg.id,
            material_unit_id=sample_unit.id,
            component_quantity=2,
        )
        db_session.add(comp)
        db_session.flush()

        with pytest.raises(MaterialUnitInUseError) as exc:
            delete_unit(sample_unit.id, session=db_session)
        assert "composition" in str(exc.value).lower()


class TestGetAvailableInventory:
    """Tests for get_available_inventory function."""

    def test_available_inventory_calculation(self, db_session, product_with_inventory):
        """Available inventory from parent product.

        Feature 084: Inventory from single parent product, not aggregated.
        Product has 1000 cm inventory.
        """
        unit = create_unit(
            material_product_id=product_with_inventory.id,
            name="6-cm ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        available = get_available_inventory(unit.id, session=db_session)
        # floor(1000 / 6) = 166
        assert available == 166

    def test_available_inventory_not_round(self, db_session, product_with_inventory):
        """Available inventory uses floor not round."""
        unit = create_unit(
            material_product_id=product_with_inventory.id,
            name="7-cm ribbon",
            quantity_per_unit=7,
            session=db_session,
        )

        available = get_available_inventory(unit.id, session=db_session)
        # floor(1000 / 7) = floor(142.86) = 142
        assert available == 142

    def test_available_inventory_no_inventory(self, db_session, sample_product):
        """No inventory returns 0."""
        unit = create_unit(
            material_product_id=sample_product.id,
            name="6-cm ribbon",
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

    def test_current_cost_calculation(self, db_session, product_with_inventory):
        """Cost calculated from parent product inventory.

        Feature 084: Cost from single parent product.
        Product has 1000 cm at $0.10/cm.
        """
        unit = create_unit(
            material_product_id=product_with_inventory.id,
            name="6-cm ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        cost = get_current_cost(unit.id, session=db_session)
        # Cost = 6 * $0.10 = $0.60
        assert cost == Decimal("0.6000")

    def test_current_cost_no_inventory(self, db_session, sample_product):
        """No inventory returns 0 cost."""
        unit = create_unit(
            material_product_id=sample_product.id,
            name="6-cm ribbon",
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

    def test_preview_sufficient_inventory(self, db_session, product_with_inventory):
        """Preview with sufficient inventory.

        Feature 084: Single product allocation, not multiple.
        """
        unit = create_unit(
            material_product_id=product_with_inventory.id,
            name="6-cm ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        preview = preview_consumption(unit.id, quantity_needed=50, session=db_session)

        assert preview["can_fulfill"] is True
        assert preview["quantity_needed"] == 50
        assert preview["base_units_needed"] == 300  # 50 * 6
        assert preview["shortage_base_units"] == 0
        assert len(preview["allocations"]) == 1  # Feature 084: Single product

    def test_preview_insufficient_inventory(self, db_session, product_with_inventory):
        """Preview with insufficient inventory."""
        unit = create_unit(
            material_product_id=product_with_inventory.id,
            name="6-cm ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        # Try to consume more than available (166 units * 6 = 996 base units available)
        # Need 200 units * 6 = 1200 base units
        preview = preview_consumption(unit.id, quantity_needed=200, session=db_session)

        assert preview["can_fulfill"] is False
        assert preview["quantity_needed"] == 200
        assert preview["base_units_needed"] == 1200  # 200 * 6
        assert preview["shortage_base_units"] == 200  # 1200 - 1000

    def test_preview_single_product_allocation(self, db_session, product_with_inventory):
        """Allocation is from single parent product.

        Feature 084: No multi-product allocation anymore.
        """
        unit = create_unit(
            material_product_id=product_with_inventory.id,
            name="6-cm ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        preview = preview_consumption(unit.id, quantity_needed=100, session=db_session)

        # Single product allocation
        assert len(preview["allocations"]) == 1
        assert preview["allocations"][0]["product_id"] == product_with_inventory.id
        assert preview["allocations"][0]["base_units_consumed"] == 600.0  # 100 * 6

    def test_preview_no_inventory(self, db_session, sample_product):
        """Preview with no inventory."""
        unit = create_unit(
            material_product_id=sample_product.id,
            name="6-cm ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        preview = preview_consumption(unit.id, quantity_needed=10, session=db_session)

        assert preview["can_fulfill"] is False
        assert preview["available_base_units"] == 0
        assert len(preview["allocations"]) == 0

    def test_preview_unit_not_found(self, db_session):
        """Non-existent unit raises error."""
        with pytest.raises(MaterialUnitNotFoundError):
            preview_consumption(99999, quantity_needed=10, session=db_session)

    def test_preview_includes_cost(self, db_session, product_with_inventory):
        """Preview includes cost calculation.

        Feature 084: Cost from single product.
        Product has 1000 cm at $0.10/cm.
        """
        unit = create_unit(
            material_product_id=product_with_inventory.id,
            name="6-cm ribbon",
            quantity_per_unit=6,
            session=db_session,
        )

        preview = preview_consumption(unit.id, quantity_needed=50, session=db_session)

        # 50 units * 6 cm = 300 cm at $0.10/cm = $30
        assert float(preview["total_cost"]) == pytest.approx(30.0, rel=0.01)
