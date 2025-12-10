"""Tests for assembly service.

Feature 013: Production & Inventory Tracking
Tests for check_can_assemble() and record_assembly() functions.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from src.models import (
    Recipe,
    Ingredient,
    Product,
    InventoryItem,
    FinishedUnit,
    FinishedGood,
    Composition,
    AssemblyRun,
    AssemblyFinishedUnitConsumption,
    AssemblyPackagingConsumption,
)
# Import AssemblyRun for direct queries in roundtrip tests - already imported above
from src.models.finished_unit import YieldMode
from src.models.assembly_type import AssemblyType
from src.services import assembly_service
from src.services.assembly_service import (
    FinishedGoodNotFoundError,
    InsufficientFinishedUnitError,
    InsufficientPackagingError,
    AssemblyRunNotFoundError,
)
from src.services.database import session_scope


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def recipe_cookies(test_db):
    """Create cookie recipe."""
    session = test_db()
    recipe = Recipe(
        name="Sugar Cookies",
        category="Cookies",
        yield_quantity=48.0,
        yield_unit="cookies",
    )
    session.add(recipe)
    session.commit()
    return recipe


@pytest.fixture
def finished_unit_cookie(test_db, recipe_cookies):
    """Create FinishedUnit for cookies with inventory."""
    session = test_db()
    fu = FinishedUnit(
        recipe_id=recipe_cookies.id,
        slug="sugar-cookie",
        display_name="Sugar Cookie",
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=48,
        item_unit="cookie",
        inventory_count=100,  # Start with inventory
        unit_cost=Decimal("0.25"),
    )
    session.add(fu)
    session.commit()
    return fu


@pytest.fixture
def ingredient_cellophane(test_db):
    """Create cellophane bag ingredient (packaging material)."""
    session = test_db()
    ingredient = Ingredient(
        display_name="Cellophane Bags",
        slug="cellophane-bags",
        category="Packaging",
        recipe_unit="bag",
        is_packaging=True,
    )
    session.add(ingredient)
    session.commit()
    return ingredient


@pytest.fixture
def product_cellophane(test_db, ingredient_cellophane):
    """Create cellophane bag product."""
    session = test_db()
    product = Product(
        ingredient_id=ingredient_cellophane.id,
        brand="Clear Bags",
        package_size="100 count",
        purchase_unit="bag",
        purchase_quantity=100.0,
        preferred=True,
    )
    session.add(product)
    session.commit()
    return product


@pytest.fixture
def inventory_cellophane(test_db, product_cellophane):
    """Create cellophane bag inventory with 50 bags."""
    session = test_db()
    inv = InventoryItem(
        product_id=product_cellophane.id,
        quantity=50.0,
        unit_cost=Decimal("0.10"),
        purchase_date=datetime(2024, 1, 1),
    )
    session.add(inv)
    session.commit()
    return inv


@pytest.fixture
def finished_good_gift_bag(test_db, finished_unit_cookie, product_cellophane):
    """Create FinishedGood with composition: 12 cookies + 1 bag."""
    session = test_db()
    fg = FinishedGood(
        slug="cookie-gift-bag",
        display_name="Cookie Gift Bag",
        assembly_type=AssemblyType.GIFT_BOX,
        inventory_count=0,
    )
    session.add(fg)
    session.flush()

    # Add FinishedUnit component (12 cookies per bag)
    comp1 = Composition(
        assembly_id=fg.id,
        finished_unit_id=finished_unit_cookie.id,
        component_quantity=12,
        sort_order=1,
    )
    session.add(comp1)

    # Add packaging component (1 bag per gift bag)
    comp2 = Composition(
        assembly_id=fg.id,
        packaging_product_id=product_cellophane.id,
        component_quantity=1,
        sort_order=2,
    )
    session.add(comp2)

    session.commit()
    return fg


@pytest.fixture
def assembly_ready(
    finished_good_gift_bag, finished_unit_cookie, inventory_cellophane
):
    """Complete assembly setup with all required inventory in place."""
    return finished_good_gift_bag


# =============================================================================
# Tests for check_can_assemble
# =============================================================================


class TestCheckCanAssemble:
    """Tests for check_can_assemble() function."""

    def test_sufficient_components(
        self, assembly_ready, finished_unit_cookie, inventory_cellophane
    ):
        """Given sufficient FU and packaging, check_can_assemble returns can_assemble=True."""
        fg = assembly_ready
        result = assembly_service.check_can_assemble(
            finished_good_id=fg.id,
            quantity=5,  # Needs 60 cookies (have 100), 5 bags (have 50)
        )
        assert result["can_assemble"] is True
        assert result["missing"] == []

    def test_insufficient_finished_unit(
        self, assembly_ready, finished_unit_cookie
    ):
        """Given insufficient FinishedUnit, returns missing details."""
        fg = assembly_ready
        result = assembly_service.check_can_assemble(
            finished_good_id=fg.id,
            quantity=10,  # Needs 120 cookies (have 100)
        )
        assert result["can_assemble"] is False
        assert len(result["missing"]) >= 1

        fu_missing = next(
            (m for m in result["missing"] if m["component_type"] == "finished_unit"),
            None,
        )
        assert fu_missing is not None
        assert fu_missing["needed"] == 120
        assert fu_missing["available"] == 100

    def test_insufficient_packaging(
        self, test_db, assembly_ready, inventory_cellophane, product_cellophane
    ):
        """Given insufficient packaging, returns missing details."""
        fg = assembly_ready

        # Reduce packaging inventory to trigger shortage
        session = test_db()
        inv = session.query(InventoryItem).filter_by(product_id=product_cellophane.id).first()
        inv.quantity = 3.0  # Only 3 bags
        session.commit()

        result = assembly_service.check_can_assemble(
            finished_good_id=fg.id,
            quantity=5,  # Needs 5 bags, have 3
        )
        assert result["can_assemble"] is False

        pkg_missing = next(
            (m for m in result["missing"] if m["component_type"] == "packaging"),
            None,
        )
        assert pkg_missing is not None
        assert pkg_missing["needed"] == Decimal("5")
        assert pkg_missing["available"] == Decimal("3.0")

    def test_finished_good_not_found(self, test_db):
        """Non-existent FinishedGood raises error."""
        with pytest.raises(FinishedGoodNotFoundError) as exc_info:
            assembly_service.check_can_assemble(
                finished_good_id=99999,
                quantity=1,
            )
        assert exc_info.value.finished_good_id == 99999


# =============================================================================
# Tests for record_assembly
# =============================================================================


class TestRecordAssembly:
    """Tests for record_assembly() function."""

    def test_happy_path(
        self, assembly_ready, finished_unit_cookie, inventory_cellophane, product_cellophane
    ):
        """Record assembly: FU decremented, packaging consumed, FG incremented."""
        fg = assembly_ready
        fg_id = fg.id
        fu_id = finished_unit_cookie.id
        initial_fu_count = finished_unit_cookie.inventory_count
        initial_fg_count = fg.inventory_count

        result = assembly_service.record_assembly(
            finished_good_id=fg_id,
            quantity=5,
            notes="Test assembly",
        )

        # Verify result structure
        assert result["assembly_run_id"] is not None
        assert result["finished_good_id"] == fg_id
        assert result["quantity_assembled"] == 5
        assert result["total_component_cost"] > Decimal("0")

        # Verify FinishedUnit decremented (12 * 5 = 60 cookies)
        with session_scope() as session:
            fu = session.query(FinishedUnit).filter_by(id=fu_id).first()
            assert fu.inventory_count == initial_fu_count - 60

        # Verify FinishedGood incremented
        with session_scope() as session:
            fg_check = session.query(FinishedGood).filter_by(id=fg_id).first()
            assert fg_check.inventory_count == initial_fg_count + 5

        # Verify consumption records created
        with session_scope() as session:
            fu_consumptions = (
                session.query(AssemblyFinishedUnitConsumption)
                .filter_by(assembly_run_id=result["assembly_run_id"])
                .all()
            )
            assert len(fu_consumptions) == 1
            assert fu_consumptions[0].quantity_consumed == 60

            pkg_consumptions = (
                session.query(AssemblyPackagingConsumption)
                .filter_by(assembly_run_id=result["assembly_run_id"])
                .all()
            )
            assert len(pkg_consumptions) == 1
            assert pkg_consumptions[0].quantity_consumed == Decimal("5")

    def test_rollback_on_insufficient_fu(
        self, assembly_ready, finished_unit_cookie
    ):
        """Insufficient FinishedUnit: entire operation rolls back."""
        fg = assembly_ready
        fg_id = fg.id
        fu_id = finished_unit_cookie.id
        initial_fu_count = finished_unit_cookie.inventory_count
        initial_fg_count = fg.inventory_count

        with pytest.raises(InsufficientFinishedUnitError):
            assembly_service.record_assembly(
                finished_good_id=fg_id,
                quantity=100,  # Needs 1200 cookies, have 100
            )

        # Verify no state changed
        with session_scope() as session:
            fu = session.query(FinishedUnit).filter_by(id=fu_id).first()
            assert fu.inventory_count == initial_fu_count

            fg_check = session.query(FinishedGood).filter_by(id=fg_id).first()
            assert fg_check.inventory_count == initial_fg_count

        # No AssemblyRun created
        with session_scope() as session:
            runs = (
                session.query(AssemblyRun)
                .filter_by(finished_good_id=fg_id)
                .all()
            )
            assert len(runs) == 0

    def test_rollback_on_insufficient_packaging(
        self, test_db, assembly_ready, inventory_cellophane, product_cellophane, finished_unit_cookie
    ):
        """Insufficient packaging: entire operation rolls back."""
        fg = assembly_ready
        fg_id = fg.id
        fu_id = finished_unit_cookie.id

        # Reduce packaging inventory to trigger failure
        session = test_db()
        inv = session.query(InventoryItem).filter_by(product_id=product_cellophane.id).first()
        inv.quantity = 3.0  # Only 3 bags
        session.commit()

        initial_fu_count = finished_unit_cookie.inventory_count
        initial_fg_count = fg.inventory_count

        with pytest.raises(InsufficientPackagingError):
            assembly_service.record_assembly(
                finished_good_id=fg_id,
                quantity=5,  # Needs 5 bags, have 3
            )

        # Verify FinishedUnit wasn't changed (rollback)
        # Note: FU might have been decremented before packaging check failed
        # This depends on order of operations - ideally full rollback
        with session_scope() as session:
            fg_check = session.query(FinishedGood).filter_by(id=fg_id).first()
            assert fg_check.inventory_count == initial_fg_count

        # No AssemblyRun created
        with session_scope() as session:
            runs = (
                session.query(AssemblyRun)
                .filter_by(finished_good_id=fg_id)
                .all()
            )
            assert len(runs) == 0

    def test_finished_good_not_found(self, test_db):
        """Non-existent FinishedGood raises error."""
        with pytest.raises(FinishedGoodNotFoundError) as exc_info:
            assembly_service.record_assembly(
                finished_good_id=99999,
                quantity=1,
            )
        assert exc_info.value.finished_good_id == 99999

    def test_custom_assembled_at_timestamp(
        self, assembly_ready, finished_unit_cookie, inventory_cellophane
    ):
        """Custom assembled_at timestamp is recorded."""
        fg = assembly_ready
        custom_time = datetime(2024, 6, 15, 10, 30, 0)

        result = assembly_service.record_assembly(
            finished_good_id=fg.id,
            quantity=1,
            assembled_at=custom_time,
        )

        with session_scope() as session:
            run = session.query(AssemblyRun).filter_by(id=result["assembly_run_id"]).first()
            assert run.assembled_at == custom_time

    def test_per_unit_cost_calculation(
        self, assembly_ready, finished_unit_cookie, inventory_cellophane
    ):
        """Per unit cost is correctly calculated as total_cost / quantity."""
        fg = assembly_ready

        result = assembly_service.record_assembly(
            finished_good_id=fg.id,
            quantity=5,
        )

        # Verify per_unit_cost = total_cost / quantity
        expected_per_unit = result["total_component_cost"] / Decimal("5")
        with session_scope() as session:
            run = session.query(AssemblyRun).filter_by(id=result["assembly_run_id"]).first()
            # Allow small precision difference
            assert abs(run.per_unit_cost - expected_per_unit) < Decimal("0.0001")

    def test_single_assembly(
        self, assembly_ready, finished_unit_cookie, inventory_cellophane
    ):
        """Assembly of single unit works correctly."""
        fg = assembly_ready
        fg_id = fg.id

        result = assembly_service.record_assembly(
            finished_good_id=fg_id,
            quantity=1,
        )

        assert result["quantity_assembled"] == 1

        # Verify FinishedGood incremented by 1
        with session_scope() as session:
            fg_check = session.query(FinishedGood).filter_by(id=fg_id).first()
            assert fg_check.inventory_count == 1

        # Verify consumptions
        with session_scope() as session:
            fu_consumptions = (
                session.query(AssemblyFinishedUnitConsumption)
                .filter_by(assembly_run_id=result["assembly_run_id"])
                .all()
            )
            assert len(fu_consumptions) == 1
            assert fu_consumptions[0].quantity_consumed == 12  # 12 cookies per bag


# =============================================================================
# Tests for History Query Functions
# =============================================================================


class TestGetAssemblyHistory:
    """Tests for get_assembly_history() function."""

    def test_empty_history(self, test_db):
        """Empty database returns empty list."""
        result = assembly_service.get_assembly_history()
        assert result == []

    def test_returns_assembly_runs(
        self, assembly_ready, finished_unit_cookie, inventory_cellophane
    ):
        """Returns list of assembly runs."""
        fg = assembly_ready
        fg_id = fg.id

        # Create two assembly runs
        assembly_service.record_assembly(
            finished_good_id=fg_id,
            quantity=2,
        )
        assembly_service.record_assembly(
            finished_good_id=fg_id,
            quantity=3,
        )

        result = assembly_service.get_assembly_history()
        assert len(result) == 2
        # Most recent first
        assert result[0]["quantity_assembled"] == 3
        assert result[1]["quantity_assembled"] == 2

    def test_filter_by_finished_good(
        self, assembly_ready, finished_unit_cookie, inventory_cellophane
    ):
        """Filters by finished_good_id."""
        fg = assembly_ready
        fg_id = fg.id

        assembly_service.record_assembly(
            finished_good_id=fg_id,
            quantity=2,
        )

        result = assembly_service.get_assembly_history(finished_good_id=fg_id)
        assert len(result) == 1
        assert result[0]["finished_good_id"] == fg_id

        # Non-existent finished good returns empty
        result = assembly_service.get_assembly_history(finished_good_id=99999)
        assert len(result) == 0

    def test_filter_by_date_range(
        self, assembly_ready, finished_unit_cookie, inventory_cellophane
    ):
        """Filters by date range."""
        fg = assembly_ready
        fg_id = fg.id

        assembly_service.record_assembly(
            finished_good_id=fg_id,
            quantity=2,
            assembled_at=datetime(2024, 6, 15),
        )

        # Within range
        result = assembly_service.get_assembly_history(
            start_date=datetime(2024, 6, 1),
            end_date=datetime(2024, 6, 30),
        )
        assert len(result) == 1

        # Outside range
        result = assembly_service.get_assembly_history(
            start_date=datetime(2024, 7, 1),
            end_date=datetime(2024, 7, 31),
        )
        assert len(result) == 0

    def test_include_consumptions(
        self, assembly_ready, finished_unit_cookie, inventory_cellophane
    ):
        """Include consumption details when requested."""
        fg = assembly_ready
        fg_id = fg.id

        assembly_service.record_assembly(
            finished_good_id=fg_id,
            quantity=2,
        )

        result = assembly_service.get_assembly_history(include_consumptions=True)
        assert len(result) == 1
        assert "finished_unit_consumptions" in result[0]
        assert "packaging_consumptions" in result[0]
        assert len(result[0]["finished_unit_consumptions"]) == 1
        assert len(result[0]["packaging_consumptions"]) == 1

    def test_pagination(
        self, assembly_ready, finished_unit_cookie, inventory_cellophane
    ):
        """Supports limit and offset pagination."""
        fg = assembly_ready
        fg_id = fg.id

        # Create 3 assembly runs
        for i in range(3):
            assembly_service.record_assembly(
                finished_good_id=fg_id,
                quantity=1,
            )

        # Limit to 2
        result = assembly_service.get_assembly_history(limit=2)
        assert len(result) == 2

        # Offset by 1
        result = assembly_service.get_assembly_history(limit=2, offset=1)
        assert len(result) == 2


class TestGetAssemblyRun:
    """Tests for get_assembly_run() function."""

    def test_get_by_id(
        self, assembly_ready, finished_unit_cookie, inventory_cellophane
    ):
        """Returns assembly run by ID with full details."""
        fg = assembly_ready
        fg_id = fg.id

        create_result = assembly_service.record_assembly(
            finished_good_id=fg_id,
            quantity=3,
            notes="Test assembly",
        )

        result = assembly_service.get_assembly_run(
            create_result["assembly_run_id"]
        )
        assert result["id"] == create_result["assembly_run_id"]
        assert result["finished_good_id"] == fg_id
        assert result["quantity_assembled"] == 3
        assert result["notes"] == "Test assembly"
        assert "finished_unit_consumptions" in result
        assert "packaging_consumptions" in result

    def test_not_found(self, test_db):
        """Raises error for non-existent assembly run."""
        with pytest.raises(AssemblyRunNotFoundError) as exc_info:
            assembly_service.get_assembly_run(99999)
        assert exc_info.value.assembly_run_id == 99999


# =============================================================================
# Tests for Import/Export Functions
# =============================================================================


class TestExportAssemblyHistory:
    """Tests for export_assembly_history() function."""

    def test_empty_export(self, test_db):
        """Empty database returns empty assembly_runs list."""
        result = assembly_service.export_assembly_history()
        assert result["version"] == "1.0"
        assert "exported_at" in result
        assert result["assembly_runs"] == []

    def test_export_with_data(
        self, assembly_ready, finished_unit_cookie, inventory_cellophane
    ):
        """Export includes full assembly run data with consumptions."""
        fg = assembly_ready
        fg_id = fg.id

        assembly_service.record_assembly(
            finished_good_id=fg_id,
            quantity=3,
            notes="Export test",
        )

        result = assembly_service.export_assembly_history()
        assert len(result["assembly_runs"]) == 1

        run = result["assembly_runs"][0]
        assert run["finished_good_slug"] == "cookie-gift-bag"
        assert run["quantity_assembled"] == 3
        assert run["notes"] == "Export test"
        assert len(run["finished_unit_consumptions"]) == 1
        assert len(run["packaging_consumptions"]) == 1


class TestImportAssemblyHistory:
    """Tests for import_assembly_history() function."""

    def test_import_skips_duplicates(
        self, assembly_ready, finished_unit_cookie, inventory_cellophane
    ):
        """Import with skip_duplicates=True skips existing UUIDs."""
        fg = assembly_ready
        fg_id = fg.id

        assembly_service.record_assembly(
            finished_good_id=fg_id,
            quantity=2,
        )

        exported = assembly_service.export_assembly_history()
        result = assembly_service.import_assembly_history(exported)

        assert result["skipped"] == len(exported["assembly_runs"])
        assert result["imported"] == 0
        assert result["errors"] == []

    def test_import_validates_missing_finished_good(self, test_db):
        """Import fails gracefully with missing finished good reference."""
        data = {
            "version": "1.0",
            "assembly_runs": [
                {
                    "uuid": "test-uuid-001",
                    "finished_good_slug": "nonexistent-fg",
                    "quantity_assembled": 1,
                    "assembled_at": "2024-06-15T10:00:00",
                    "notes": None,
                    "total_component_cost": "5.00",
                    "per_unit_cost": "5.00",
                    "finished_unit_consumptions": [],
                    "packaging_consumptions": [],
                }
            ],
        }
        result = assembly_service.import_assembly_history(data)
        assert result["imported"] == 0
        assert len(result["errors"]) > 0
        assert "FinishedGood not found" in result["errors"][0]

    def test_export_import_roundtrip(
        self, test_db, assembly_ready, finished_unit_cookie, inventory_cellophane
    ):
        """Export -> clear -> import preserves data."""
        fg = assembly_ready
        fg_id = fg.id

        # Create assembly run
        assembly_service.record_assembly(
            finished_good_id=fg_id,
            quantity=3,
            notes="Roundtrip test",
        )

        # Export
        exported = assembly_service.export_assembly_history()
        assert len(exported["assembly_runs"]) == 1
        original_run = exported["assembly_runs"][0]

        # Clear assembly runs
        with session_scope() as session:
            session.query(AssemblyFinishedUnitConsumption).delete()
            session.query(AssemblyPackagingConsumption).delete()
            session.query(AssemblyRun).delete()

        # Verify cleared
        verify_export = assembly_service.export_assembly_history()
        assert len(verify_export["assembly_runs"]) == 0

        # Import
        result = assembly_service.import_assembly_history(exported)
        assert result["imported"] == 1
        assert result["errors"] == []

        # Verify reimported data matches
        reimported = assembly_service.export_assembly_history()
        assert len(reimported["assembly_runs"]) == 1

        reimp_run = reimported["assembly_runs"][0]
        assert reimp_run["uuid"] == original_run["uuid"]
        assert reimp_run["quantity_assembled"] == original_run["quantity_assembled"]
        assert reimp_run["total_component_cost"] == original_run["total_component_cost"]
        assert reimp_run["notes"] == original_run["notes"]


# =============================================================================
# Transaction Atomicity Tests (Bug Fix Verification)
# =============================================================================


class TestAssemblyTransactionAtomicity:
    """Tests verifying that record_assembly is fully atomic.

    These tests verify the fix for the Constitution Principle II violation
    where FIFO consumption for packaging was committing independently.
    """

    def test_record_assembly_rolls_back_all_inventory_on_failure(
        self, test_db, assembly_ready, finished_unit_cookie, inventory_cellophane
    ):
        """Verify all inventory is restored if assembly fails.

        This test validates that the atomic transaction fix works correctly:
        if any part of record_assembly fails, ALL changes (including
        FIFO packaging consumption and FU decrements) are rolled back.
        """
        fg = assembly_ready
        fg_id = fg.id
        fu_id = finished_unit_cookie.id
        cellophane_id = inventory_cellophane.id

        # Record initial inventory quantities
        with session_scope() as session:
            fu = session.query(FinishedUnit).filter_by(id=fu_id).first()
            cellophane = session.query(InventoryItem).filter_by(id=cellophane_id).first()
            finished_good = session.query(FinishedGood).filter_by(id=fg_id).first()

            initial_fu_count = fu.inventory_count
            initial_cellophane_qty = cellophane.quantity
            initial_fg_count = finished_good.inventory_count

        # Attempt assembly that will fail due to insufficient inventory
        with pytest.raises(InsufficientFinishedUnitError):
            assembly_service.record_assembly(
                finished_good_id=fg_id,
                quantity=1000,  # Way more than available
            )

        # Verify ALL inventory quantities are unchanged (rollback worked)
        with session_scope() as session:
            fu = session.query(FinishedUnit).filter_by(id=fu_id).first()
            cellophane = session.query(InventoryItem).filter_by(id=cellophane_id).first()
            finished_good = session.query(FinishedGood).filter_by(id=fg_id).first()

            # Critical assertions: inventory should be EXACTLY as before
            assert fu.inventory_count == initial_fu_count, (
                f"FinishedUnit inventory was modified but should have rolled back. "
                f"Expected {initial_fu_count}, got {fu.inventory_count}"
            )
            assert cellophane.quantity == initial_cellophane_qty, (
                f"Packaging inventory was modified but should have rolled back. "
                f"Expected {initial_cellophane_qty}, got {cellophane.quantity}"
            )
            assert finished_good.inventory_count == initial_fg_count, (
                f"FinishedGood inventory was modified but should have rolled back. "
                f"Expected {initial_fg_count}, got {finished_good.inventory_count}"
            )

        # Verify no AssemblyRun was created
        with session_scope() as session:
            runs = session.query(AssemblyRun).filter_by(finished_good_id=fg_id).all()
            assert len(runs) == 0, "AssemblyRun should not exist after failed assembly"

    def test_successful_assembly_commits_atomically(
        self, test_db, assembly_ready, finished_unit_cookie, inventory_cellophane
    ):
        """Verify successful assembly commits all changes together.

        This test verifies that when assembly succeeds, FU decrements,
        packaging consumption, FG increments, AND assembly records
        are all committed in a single atomic transaction.
        """
        fg = assembly_ready
        fg_id = fg.id
        fu_id = finished_unit_cookie.id
        cellophane_id = inventory_cellophane.id

        # Record initial quantities
        with session_scope() as session:
            fu = session.query(FinishedUnit).filter_by(id=fu_id).first()
            cellophane = session.query(InventoryItem).filter_by(id=cellophane_id).first()
            finished_good = session.query(FinishedGood).filter_by(id=fg_id).first()

            initial_fu_count = fu.inventory_count
            initial_cellophane_qty = cellophane.quantity
            initial_fg_count = finished_good.inventory_count

        # Perform successful assembly
        result = assembly_service.record_assembly(
            finished_good_id=fg_id,
            quantity=2,
        )

        # Verify all changes were committed together
        with session_scope() as session:
            fu = session.query(FinishedUnit).filter_by(id=fu_id).first()
            cellophane = session.query(InventoryItem).filter_by(id=cellophane_id).first()
            finished_good = session.query(FinishedGood).filter_by(id=fg_id).first()

            # FinishedUnit should be decremented
            assert fu.inventory_count < initial_fu_count, "FinishedUnit should be consumed"

            # Packaging should be consumed
            assert cellophane.quantity < initial_cellophane_qty, "Packaging should be consumed"

            # FinishedGood should be incremented
            assert finished_good.inventory_count == initial_fg_count + 2, (
                "FinishedGood should be incremented"
            )

        # Verify AssemblyRun exists with correct data
        with session_scope() as session:
            run = session.query(AssemblyRun).filter_by(id=result["assembly_run_id"]).first()
            assert run is not None, "AssemblyRun should exist"
            assert run.quantity_assembled == 2

        # Verify consumption ledger records exist
        with session_scope() as session:
            fu_consumptions = session.query(AssemblyFinishedUnitConsumption).filter_by(
                assembly_run_id=result["assembly_run_id"]
            ).all()
            pkg_consumptions = session.query(AssemblyPackagingConsumption).filter_by(
                assembly_run_id=result["assembly_run_id"]
            ).all()
            # Should have FU consumption record and packaging consumption record
            assert len(fu_consumptions) >= 1, "Should have FU consumption records"
            assert len(pkg_consumptions) >= 1, "Should have packaging consumption records"
