"""Tests for Material Consumption History (Feature 047 - WP08).

Tests for:
- Historical queries return snapshot data (not current catalog)
- Snapshot preserved after catalog rename
- Date range filtering
- Material/product filtering
"""

import pytest
from datetime import date, timedelta
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
    update_product,
)
from src.services.material_unit_service import create_unit
from src.services.material_purchase_service import record_purchase
from src.services.material_consumption_service import (
    record_material_consumption,
    get_consumption_history,
)


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
        assembly_type=AssemblyType.BUNDLE,
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
def material_with_inventory(db_session, sample_supplier):
    """Create material with product and inventory."""
    cat = create_category("Ribbons", session=db_session)
    subcat = create_subcategory(cat.id, "Satin", session=db_session)
    mat = create_material(subcat.id, "Red Satin", "linear_cm", session=db_session)

    prod = create_product(
        material_id=mat.id,
        name="Original Product Name",  # Will be renamed later
        package_quantity=1200,
        package_unit="inches",
        supplier_id=sample_supplier.id,
        session=db_session,
    )

    record_purchase(
        product_id=prod.id,
        supplier_id=sample_supplier.id,
        purchase_date=date.today(),
        packages_purchased=1,
        package_price=Decimal("96.00"),
        session=db_session,
    )

    return {
        "category": cat,
        "subcategory": subcat,
        "material": mat,
        "product": prod,
        "supplier": sample_supplier,
    }


@pytest.fixture
def material_unit_with_composition(db_session, sample_finished_good, material_with_inventory):
    """Create MaterialUnit and add to FinishedGood composition."""
    unit = create_unit(
        material_product_id=material_with_inventory["product"].id,
        name="6-inch ribbon",
        quantity_per_unit=6,
        session=db_session,
    )

    comp = Composition.create_material_unit_composition(
        assembly_id=sample_finished_good.id,
        material_unit_id=unit.id,
        quantity=2,  # 2 units per assembly
    )
    db_session.add(comp)
    db_session.commit()

    return {
        "unit": unit,
        "composition": comp,
        **material_with_inventory,
    }


# =============================================================================
# Snapshot Preservation Tests
# =============================================================================


class TestSnapshotPreservation:
    """Tests for historical snapshot preservation."""

    def test_snapshot_preserves_original_product_name(
        self, db_session, sample_assembly_run, sample_finished_good, material_unit_with_composition
    ):
        """Snapshot shows original product name even after rename."""
        product = material_unit_with_composition["product"]
        original_name = product.display_name

        # Record consumption
        record_material_consumption(
            assembly_run_id=sample_assembly_run.id,
            finished_good_id=sample_finished_good.id,
            assembly_quantity=10,
            session=db_session,
        )

        # Rename the product
        update_product(
            product_id=product.id,
            name="New Product Name",
            session=db_session,
        )

        # Query history
        history = get_consumption_history(
            assembly_run_id=sample_assembly_run.id,
            session=db_session,
        )

        # Snapshot should show ORIGINAL name
        assert len(history) > 0
        assert history[0]["product_name"] == original_name
        assert history[0]["product_name"] != "New Product Name"

    def test_snapshot_preserves_material_hierarchy(
        self, db_session, sample_assembly_run, sample_finished_good, material_unit_with_composition
    ):
        """Snapshot preserves category/subcategory/material names."""
        record_material_consumption(
            assembly_run_id=sample_assembly_run.id,
            finished_good_id=sample_finished_good.id,
            assembly_quantity=5,
            session=db_session,
        )

        history = get_consumption_history(
            assembly_run_id=sample_assembly_run.id,
            session=db_session,
        )

        assert len(history) > 0
        record = history[0]
        assert record["material_name"] == "Red Satin"
        assert record["subcategory_name"] == "Satin"
        assert record["category_name"] == "Ribbons"

    def test_snapshot_preserves_cost_at_consumption_time(
        self, db_session, sample_assembly_run, sample_finished_good, material_unit_with_composition
    ):
        """Snapshot preserves unit cost at time of consumption.

        F058: weighted_avg_cost removed from MaterialProduct.
        Now calculate weighted average from MaterialInventoryItem records.
        """
        from src.models.material_inventory_item import MaterialInventoryItem

        product = material_unit_with_composition["product"]

        # Calculate original weighted average from inventory items (F058)
        inv_items = (
            db_session.query(MaterialInventoryItem)
            .filter(MaterialInventoryItem.material_product_id == product.id)
            .all()
        )
        total_value = sum(
            Decimal(str(item.quantity_remaining)) * item.cost_per_unit for item in inv_items
        )
        total_qty = sum(Decimal(str(item.quantity_remaining)) for item in inv_items)
        original_cost = total_value / total_qty if total_qty > 0 else Decimal("0")

        # Record consumption
        consumptions = record_material_consumption(
            assembly_run_id=sample_assembly_run.id,
            finished_good_id=sample_finished_good.id,
            assembly_quantity=10,
            session=db_session,
        )

        # Record another purchase at different price (changes weighted average)
        record_purchase(
            product_id=product.id,
            supplier_id=material_unit_with_composition["supplier"].id,
            purchase_date=date.today(),
            packages_purchased=1,
            package_price=Decimal("192.00"),  # Double the price
            session=db_session,
        )

        db_session.refresh(product)

        # Calculate new weighted average from inventory items (F058)
        inv_items_new = (
            db_session.query(MaterialInventoryItem)
            .filter(MaterialInventoryItem.material_product_id == product.id)
            .all()
        )
        total_value_new = sum(
            Decimal(str(item.quantity_remaining)) * item.cost_per_unit for item in inv_items_new
        )
        total_qty_new = sum(Decimal(str(item.quantity_remaining)) for item in inv_items_new)
        new_cost = total_value_new / total_qty_new if total_qty_new > 0 else Decimal("0")

        # Cost should have changed (new inventory item at different price)
        assert new_cost != original_cost

        # But history should show original cost (to_dict returns unit_cost as string)
        history = get_consumption_history(
            assembly_run_id=sample_assembly_run.id,
            session=db_session,
        )

        assert len(history) > 0
        # The consumption record's unit_cost is the cost from the FIFO lot consumed
        # It should be close to the original cost (may have minor decimal differences)
        history_cost = Decimal(history[0]["unit_cost"])
        assert abs(history_cost - original_cost) < Decimal("0.0001")


# =============================================================================
# Filtering Tests
# =============================================================================


class TestHistoryFiltering:
    """Tests for consumption history filtering."""

    def test_filter_by_assembly_run(
        self, db_session, sample_finished_good, material_unit_with_composition
    ):
        """History can be filtered by assembly_run_id."""
        # Create two assembly runs
        run1 = AssemblyRun(
            finished_good_id=sample_finished_good.id,
            quantity_assembled=5,
            total_component_cost=Decimal("0"),
            per_unit_cost=Decimal("0"),
        )
        run2 = AssemblyRun(
            finished_good_id=sample_finished_good.id,
            quantity_assembled=10,
            total_component_cost=Decimal("0"),
            per_unit_cost=Decimal("0"),
        )
        db_session.add_all([run1, run2])
        db_session.flush()

        # Record consumption for both
        record_material_consumption(
            assembly_run_id=run1.id,
            finished_good_id=sample_finished_good.id,
            assembly_quantity=5,
            session=db_session,
        )
        record_material_consumption(
            assembly_run_id=run2.id,
            finished_good_id=sample_finished_good.id,
            assembly_quantity=10,
            session=db_session,
        )

        # Filter by run1
        history1 = get_consumption_history(
            assembly_run_id=run1.id,
            session=db_session,
        )

        # Filter by run2
        history2 = get_consumption_history(
            assembly_run_id=run2.id,
            session=db_session,
        )

        # Each should return only their own consumption
        assert len(history1) > 0
        assert len(history2) > 0
        assert all(h.get("assembly_run_id") == run1.id for h in history1)
        assert all(h.get("assembly_run_id") == run2.id for h in history2)

    def test_empty_history_for_no_consumptions(self, db_session, sample_assembly_run):
        """History returns empty list when no consumptions recorded."""
        history = get_consumption_history(
            assembly_run_id=sample_assembly_run.id,
            session=db_session,
        )

        assert history == []


# =============================================================================
# Data Structure Tests
# =============================================================================


class TestHistoryDataStructure:
    """Tests for consumption history data structure."""

    def test_history_includes_all_snapshot_fields(
        self, db_session, sample_assembly_run, sample_finished_good, material_unit_with_composition
    ):
        """History includes all required snapshot fields."""
        record_material_consumption(
            assembly_run_id=sample_assembly_run.id,
            finished_good_id=sample_finished_good.id,
            assembly_quantity=10,
            session=db_session,
        )

        history = get_consumption_history(
            assembly_run_id=sample_assembly_run.id,
            session=db_session,
        )

        assert len(history) > 0
        record = history[0]

        # Check all required fields present
        assert "product_name" in record
        assert "material_name" in record
        assert "subcategory_name" in record
        assert "category_name" in record
        assert "quantity_consumed" in record
        assert "unit_cost" in record
        assert "total_cost" in record

    def test_history_calculates_total_cost(
        self, db_session, sample_assembly_run, sample_finished_good, material_unit_with_composition
    ):
        """History total_cost = quantity_consumed * unit_cost."""
        record_material_consumption(
            assembly_run_id=sample_assembly_run.id,
            finished_good_id=sample_finished_good.id,
            assembly_quantity=10,
            session=db_session,
        )

        history = get_consumption_history(
            assembly_run_id=sample_assembly_run.id,
            session=db_session,
        )

        assert len(history) > 0
        record = history[0]

        # to_dict() returns unit_cost and total_cost as strings
        unit_cost = Decimal(record["unit_cost"])
        total_cost = Decimal(record["total_cost"])
        expected_total = Decimal(str(record["quantity_consumed"])) * unit_cost
        assert abs(total_cost - expected_total) < Decimal("0.01")
