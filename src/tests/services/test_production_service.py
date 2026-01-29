"""Tests for production_service module.

Feature 008: Production Tracking
"""

import pytest
from decimal import Decimal
from datetime import date

from src.services import production_service
from src.services.production_service import (
    get_production_records,
    get_production_total,
    can_assemble_package,
    update_package_status,
    get_production_progress,
    get_dashboard_summary,
    get_recipe_cost_breakdown,
    InsufficientInventoryError,
    RecipeNotFoundError,
    InvalidStatusTransitionError,
    IncompleteProductionError,
    AssignmentNotFoundError,
)
from src.services.event_service import EventNotFoundError
from src.services.exceptions import ValidationError
from src.models import PackageStatus, ProductionRecord
from src.services.database import session_scope


def _create_production_record(event_id, recipe_id, batches, actual_cost=Decimal("1.10"), notes=None):
    """
    Helper to create ProductionRecord directly for test setup.

    This replaces the removed record_production() function for test purposes.
    Unlike the old function, this does NOT consume inventory or validate
    anything - it simply creates a record for testing query functions.

    Args:
        event_id: Event ID
        recipe_id: Recipe ID
        batches: Number of batches
        actual_cost: Cost to record (default $1.10)
        notes: Optional notes

    Returns:
        The created ProductionRecord
    """
    with session_scope() as session:
        record = ProductionRecord(
            event_id=event_id,
            recipe_id=recipe_id,
            batches=batches,
            actual_cost=actual_cost,
            notes=notes,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        # Return a copy of values to avoid detached object issues
        record_id = record.id
    # Re-query to return attached object (for tests that need it)
    with session_scope() as session:
        return session.get(ProductionRecord, record_id)


@pytest.fixture
def setup_production_test_data(test_db):
    """Create test data for production tests."""
    from src.services import (
        ingredient_service,
        product_service,
        inventory_item_service,
        recipe_service,
    )
    from src.services import event_service, supplier_service

    # Create supplier for inventory
    supplier_result = supplier_service.create_supplier(
        name="Test Supplier",
        city="Boston",
        state="MA",
        zip_code="02101",
    )
    supplier_id = supplier_result["id"]

    # Create ingredient: flour
    flour = ingredient_service.create_ingredient(
        {
            "display_name": "All Purpose Flour",
            "category": "Flour",
            # 4-field density: 1 cup = 120g (~0.507 g/ml)
            "density_volume_value": 1.0,
            "density_volume_unit": "cup",
            "density_weight_value": 120.0,
            "density_weight_unit": "g",
        }
    )

    # Create product for flour
    flour_product = product_service.create_product(
        flour.slug,
        {
            "brand": "King Arthur",
            "package_size": "5 lb bag",
            "package_unit": "cup",
            "package_unit_quantity": Decimal("20.0"),
            "preferred": True,
        },
    )

    # Add flour to inventory (two batches at different prices for FIFO test)
    # First batch: older, $0.40 per cup
    inventory_item_1 = inventory_item_service.add_to_inventory(
        product_id=flour_product.id,
        quantity=Decimal("5.0"),
        supplier_id=supplier_id,
        unit_price=Decimal("0.40"),
        purchase_date=date(2024, 1, 1),
    )

    # Second batch: newer, $0.60 per cup
    inventory_item_2 = inventory_item_service.add_to_inventory(
        product_id=flour_product.id,
        quantity=Decimal("10.0"),
        supplier_id=supplier_id,
        unit_price=Decimal("0.60"),
        purchase_date=date(2024, 6, 1),
    )

    # Create ingredient: sugar
    sugar = ingredient_service.create_ingredient(
        {
            "display_name": "Granulated Sugar",
            "category": "Sugar",
            # 4-field density: 1 cup = 200g (~0.85 g/ml)
            "density_volume_value": 1.0,
            "density_volume_unit": "cup",
            "density_weight_value": 200.0,
            "density_weight_unit": "g",
        }
    )

    sugar_product = product_service.create_product(
        sugar.slug,
        {
            "brand": "Domino",
            "package_size": "4 lb bag",
            "package_unit": "cup",
            "package_unit_quantity": Decimal("8.0"),
            "preferred": True,
        },
    )

    sugar_inventory = inventory_item_service.add_to_inventory(
        product_id=sugar_product.id,
        quantity=Decimal("10.0"),
        supplier_id=supplier_id,
        unit_price=Decimal("0.30"),
        purchase_date=date(2024, 3, 1),
    )

    # Create recipe using the service
    recipe = recipe_service.create_recipe(
        recipe_data={
            "name": "Test Cookies",
            "category": "Cookies",
            "yield_quantity": 24,
            "yield_unit": "cookies",
        },
        ingredients_data=[
            {"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"},
            {"ingredient_id": sugar.id, "quantity": 1.0, "unit": "cup"},
        ],
    )

    # Create event using the service
    with session_scope() as session:
        event = event_service.create_event(
            name="Christmas 2024",
            event_date=date(2024, 12, 25),
            year=2024,
            session=session,
        )

    return {
        "flour": flour,
        "sugar": sugar,
        "flour_product": flour_product,
        "sugar_product": sugar_product,
        "recipe": recipe,
        "event": event,
    }


class TestGetProductionRecords:
    """Tests for get_production_records() function."""

    def test_get_production_records_empty(self, test_db, setup_production_test_data):
        """Test: Returns empty list when no production recorded."""
        data = setup_production_test_data

        with session_scope() as session:
            records = get_production_records(data["event"].id, session=session)

        assert records == []

    def test_get_production_records_with_data(self, test_db, setup_production_test_data):
        """Test: Returns all production records for event."""
        data = setup_production_test_data

        # Create production records directly (not via removed record_production)
        _create_production_record(
            event_id=data["event"].id, recipe_id=data["recipe"].id, batches=1
        )
        _create_production_record(
            event_id=data["event"].id, recipe_id=data["recipe"].id, batches=2, notes="Second batch"
        )

        with session_scope() as session:
            records = get_production_records(data["event"].id, session=session)

        assert len(records) == 2


class TestGetProductionTotal:
    """Tests for get_production_total() function."""

    def test_get_production_total_no_records(self, test_db, setup_production_test_data):
        """Test: Returns zeros when no production recorded."""
        data = setup_production_test_data

        with session_scope() as session:
            result = get_production_total(
                data["event"].id,
                data["recipe"].id,
                session=session,
            )

        assert result["batches_produced"] == 0
        assert result["total_actual_cost"] == Decimal("0.00")

    def test_get_production_total_with_records(self, test_db, setup_production_test_data):
        """Test: Correctly sums batches and costs."""
        data = setup_production_test_data

        # Create production records directly with known costs
        _create_production_record(
            event_id=data["event"].id, recipe_id=data["recipe"].id, batches=1, actual_cost=Decimal("1.10")
        )
        _create_production_record(
            event_id=data["event"].id, recipe_id=data["recipe"].id, batches=2, actual_cost=Decimal("2.40")
        )

        with session_scope() as session:
            result = get_production_total(
                data["event"].id,
                data["recipe"].id,
                session=session,
            )

        assert result["batches_produced"] == 3
        # Total: $1.10 + $2.40 = $3.50
        assert result["total_actual_cost"] == Decimal("3.50")


# ============================================================================
# Fixtures for Package Status Tests
# ============================================================================


@pytest.fixture
def setup_package_status_test_data(test_db, setup_production_test_data):
    """
    Create test data for package status tests.

    Extends setup_production_test_data with:
    - FinishedUnit linked to the recipe
    - FinishedGood (assembly) containing the FinishedUnit
    - Package containing the FinishedGood
    - Recipient
    - EventRecipientPackage (assignment)
    """
    from src.models import (
        FinishedUnit,
        FinishedGood,
        Composition,
        Package,
        PackageFinishedGood,
        Recipient,
        EventRecipientPackage,
        PackageStatus,
    )
    from src.models.finished_unit import YieldMode
    from src.models.assembly_type import AssemblyType

    data = setup_production_test_data
    session = test_db()

    # Create FinishedUnit linked to the recipe
    # Recipe yields 24 cookies per batch
    fu = FinishedUnit(
        display_name="Test Cookie Unit",
        slug="test-cookie-unit",
        recipe_id=data["recipe"].id,
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=24,
    )
    session.add(fu)
    session.flush()

    # Create FinishedGood (assembly) - a "Cookie Box" containing 12 cookies
    fg = FinishedGood(
        display_name="Cookie Box",
        slug="cookie-box",
        assembly_type=AssemblyType.CUSTOM_ORDER,
    )
    session.add(fg)
    session.flush()

    # Create Composition linking FinishedGood to FinishedUnit
    # 12 cookies per box
    composition = Composition(
        assembly_id=fg.id,
        finished_unit_id=fu.id,
        component_quantity=12,
    )
    session.add(composition)
    session.flush()

    # Create Package
    package = Package(
        name="Gift Box Package",
        description="A gift box with cookies",
        is_template=False,
    )
    session.add(package)
    session.flush()

    # Add FinishedGood to Package (1 cookie box per package)
    pfg = PackageFinishedGood(
        package_id=package.id,
        finished_good_id=fg.id,
        quantity=1,
    )
    session.add(pfg)
    session.flush()

    # Create Recipient
    recipient = Recipient(
        name="Test Recipient",
        household_name="Test Family",
    )
    session.add(recipient)
    session.flush()

    # Create EventRecipientPackage (assignment)
    erp = EventRecipientPackage(
        event_id=data["event"].id,
        recipient_id=recipient.id,
        package_id=package.id,
        quantity=1,
        status=PackageStatus.PENDING,
    )
    session.add(erp)
    session.commit()
    session.refresh(erp)

    return {
        **data,
        "finished_unit": fu,
        "finished_good": fg,
        "composition": composition,
        "package": package,
        "recipient": recipient,
        "assignment": erp,
        "assignment_id": erp.id,
    }


# ============================================================================
# Package Status Management Tests
# ============================================================================


class TestCanAssemblePackage:
    """Tests for can_assemble_package() function."""

    def test_can_assemble_all_produced(self, test_db, setup_package_status_test_data):
        """Test: Returns True when all recipes fully produced."""
        data = setup_package_status_test_data

        # Package needs: 1 package * 1 cookie box * 12 cookies = 12 cookies
        # Recipe yields 24 per batch, so 1 batch is enough
        _create_production_record(
            event_id=data["event"].id,
            recipe_id=data["recipe"].id,
            batches=1,
        )

        with session_scope() as session:
            result = can_assemble_package(data["assignment"].id, session=session)

        assert result["can_assemble"] is True
        assert len(result["missing_recipes"]) == 0

    def test_cannot_assemble_no_production(self, test_db, setup_package_status_test_data):
        """Test: Returns False when no production recorded."""
        data = setup_package_status_test_data

        with session_scope() as session:
            result = can_assemble_package(data["assignment"].id, session=session)

        assert result["can_assemble"] is False
        assert len(result["missing_recipes"]) == 1
        assert result["missing_recipes"][0]["recipe_name"] == "Test Cookies"
        assert result["missing_recipes"][0]["batches_required"] == 1
        assert result["missing_recipes"][0]["batches_produced"] == 0

    def test_can_assemble_assignment_not_found(self, test_db, setup_package_status_test_data):
        """Test: Raises AssignmentNotFoundError for invalid ID."""
        with pytest.raises(AssignmentNotFoundError):
            with session_scope() as session:
                can_assemble_package(99999, session=session)


class TestUpdatePackageStatus:
    """Tests for update_package_status() function."""

    def test_pending_to_assembled_success(self, test_db, setup_package_status_test_data):
        """Test: Can transition PENDING -> ASSEMBLED when production complete."""
        data = setup_package_status_test_data

        # Create production record (enough for the package)
        _create_production_record(
            event_id=data["event"].id,
            recipe_id=data["recipe"].id,
            batches=1,
        )

        with session_scope() as session:
            result = update_package_status(
                data["assignment"].id,
                PackageStatus.ASSEMBLED,
                session=session,
            )

        assert result.status == PackageStatus.ASSEMBLED

    def test_assembled_to_delivered_success(self, test_db, setup_package_status_test_data):
        """Test: Can transition ASSEMBLED -> DELIVERED."""
        data = setup_package_status_test_data

        # First get to ASSEMBLED state
        _create_production_record(
            event_id=data["event"].id,
            recipe_id=data["recipe"].id,
            batches=1,
        )
        with session_scope() as session:
            update_package_status(
                data["assignment"].id,
                PackageStatus.ASSEMBLED,
                session=session,
            )

        # Now transition to DELIVERED
        with session_scope() as session:
            result = update_package_status(
                data["assignment"].id,
                PackageStatus.DELIVERED,
                session=session,
                delivered_to="Left with neighbor",
            )

        assert result.status == PackageStatus.DELIVERED
        assert result.delivered_to == "Left with neighbor"

    def test_pending_to_delivered_blocked(self, test_db, setup_package_status_test_data):
        """Test: Cannot skip PENDING -> DELIVERED."""
        data = setup_package_status_test_data

        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            with session_scope() as session:
                update_package_status(
                    data["assignment"].id,
                    PackageStatus.DELIVERED,
                    session=session,
                )

        assert exc_info.value.current == PackageStatus.PENDING
        assert exc_info.value.target == PackageStatus.DELIVERED

    def test_assembled_to_pending_blocked(self, test_db, setup_package_status_test_data):
        """Test: Cannot rollback ASSEMBLED -> PENDING."""
        data = setup_package_status_test_data

        # Get to ASSEMBLED state
        _create_production_record(
            event_id=data["event"].id,
            recipe_id=data["recipe"].id,
            batches=1,
        )
        with session_scope() as session:
            update_package_status(
                data["assignment"].id,
                PackageStatus.ASSEMBLED,
                session=session,
            )

        # Try to go back to PENDING
        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            with session_scope() as session:
                update_package_status(
                    data["assignment"].id,
                    PackageStatus.PENDING,
                    session=session,
                )

        assert exc_info.value.current == PackageStatus.ASSEMBLED
        assert exc_info.value.target == PackageStatus.PENDING

    def test_delivered_to_any_blocked(self, test_db, setup_package_status_test_data):
        """Test: Cannot transition from DELIVERED."""
        data = setup_package_status_test_data

        # Get to DELIVERED state
        _create_production_record(
            event_id=data["event"].id,
            recipe_id=data["recipe"].id,
            batches=1,
        )
        with session_scope() as session:
            update_package_status(
                data["assignment"].id,
                PackageStatus.ASSEMBLED,
                session=session,
            )
        with session_scope() as session:
            update_package_status(
                data["assignment"].id,
                PackageStatus.DELIVERED,
                session=session,
            )

        # Try to go back to ASSEMBLED
        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            with session_scope() as session:
                update_package_status(
                    data["assignment"].id,
                    PackageStatus.ASSEMBLED,
                    session=session,
                )

        assert exc_info.value.current == PackageStatus.DELIVERED
        assert exc_info.value.target == PackageStatus.ASSEMBLED

    def test_assemble_incomplete_production(self, test_db, setup_package_status_test_data):
        """Test: Cannot assemble when recipes not fully produced."""
        data = setup_package_status_test_data

        # No production recorded - should fail
        with pytest.raises(IncompleteProductionError) as exc_info:
            with session_scope() as session:
                update_package_status(
                    data["assignment"].id,
                    PackageStatus.ASSEMBLED,
                    session=session,
                )

        assert exc_info.value.assignment_id == data["assignment_id"]
        assert len(exc_info.value.missing_recipes) > 0

    def test_update_status_assignment_not_found(self, test_db, setup_package_status_test_data):
        """Test: Raises AssignmentNotFoundError for invalid ID."""
        with pytest.raises(AssignmentNotFoundError):
            with session_scope() as session:
                update_package_status(
                    99999,
                    PackageStatus.ASSEMBLED,
                    session=session,
                )


# ============================================================================
# Progress & Dashboard Tests
# ============================================================================


class TestGetProductionProgress:
    """Tests for get_production_progress() function."""

    def test_progress_no_production(self, test_db, setup_package_status_test_data):
        """Test: Returns zero progress when nothing produced."""
        data = setup_package_status_test_data

        with session_scope() as session:
            progress = get_production_progress(data["event"].id, session=session)

        assert progress["event_id"] == data["event"].id
        assert progress["event_name"] == "Christmas 2024"
        assert len(progress["recipes"]) == 1
        assert progress["recipes"][0]["batches_produced"] == 0
        assert progress["recipes"][0]["is_complete"] is False
        assert progress["packages"]["pending"] == 1
        assert progress["packages"]["assembled"] == 0
        assert progress["packages"]["delivered"] == 0
        assert progress["is_complete"] is False

    def test_progress_partial_production(self, test_db, setup_package_status_test_data):
        """Test: Shows partial progress correctly."""
        data = setup_package_status_test_data

        # Create production record (1 batch, enough for this package)
        _create_production_record(
            event_id=data["event"].id,
            recipe_id=data["recipe"].id,
            batches=1,
        )

        with session_scope() as session:
            progress = get_production_progress(data["event"].id, session=session)

        # Recipe complete (1 batch is enough for 12 cookies needed)
        assert progress["recipes"][0]["batches_produced"] == 1
        assert progress["recipes"][0]["is_complete"] is True
        assert progress["costs"]["actual_total"] > Decimal("0")

    def test_progress_package_status_counts(self, test_db, setup_package_status_test_data):
        """Test: Package counts by status are accurate."""
        data = setup_package_status_test_data

        # Create production record, then assemble
        _create_production_record(
            event_id=data["event"].id,
            recipe_id=data["recipe"].id,
            batches=1,
        )
        with session_scope() as session:
            update_package_status(
                data["assignment"].id,
                PackageStatus.ASSEMBLED,
                session=session,
            )

        with session_scope() as session:
            progress = get_production_progress(data["event"].id, session=session)

        assert progress["packages"]["pending"] == 0
        assert progress["packages"]["assembled"] == 1
        assert progress["packages"]["delivered"] == 0

    def test_progress_complete_when_all_delivered(self, test_db, setup_package_status_test_data):
        """Test: is_complete True when all packages delivered."""
        data = setup_package_status_test_data

        # Create production record, assemble, deliver
        _create_production_record(
            event_id=data["event"].id,
            recipe_id=data["recipe"].id,
            batches=1,
        )
        with session_scope() as session:
            update_package_status(
                data["assignment"].id,
                PackageStatus.ASSEMBLED,
                session=session,
            )
        with session_scope() as session:
            update_package_status(
                data["assignment"].id,
                PackageStatus.DELIVERED,
                session=session,
            )

        with session_scope() as session:
            progress = get_production_progress(data["event"].id, session=session)

        assert progress["packages"]["delivered"] == 1
        assert progress["is_complete"] is True

    def test_progress_event_not_found(self, test_db, setup_package_status_test_data):
        """Test: Raises EventNotFoundError for invalid event."""
        with pytest.raises(EventNotFoundError):
            with session_scope() as session:
                get_production_progress(99999, session=session)


class TestGetDashboardSummary:
    """Tests for get_dashboard_summary() function."""

    def test_dashboard_empty(self, test_db):
        """Test: Returns empty list when no events with packages."""
        with session_scope() as session:
            result = get_dashboard_summary(session=session)
        assert result == []

    def test_dashboard_with_events(self, test_db, setup_package_status_test_data):
        """Test: Returns events with packages."""
        with session_scope() as session:
            result = get_dashboard_summary(session=session)

        assert len(result) >= 1
        # Find our test event
        event_summary = next((e for e in result if e["event_name"] == "Christmas 2024"), None)
        assert event_summary is not None
        assert event_summary["packages_total"] >= 1


class TestGetRecipeCostBreakdown:
    """Tests for get_recipe_cost_breakdown() function."""

    def test_cost_breakdown_no_production(self, test_db, setup_package_status_test_data):
        """Test: Shows zero actual costs when nothing produced."""
        data = setup_package_status_test_data

        with session_scope() as session:
            breakdown = get_recipe_cost_breakdown(data["event"].id, session=session)

        assert len(breakdown) == 1
        assert breakdown[0]["recipe_name"] == "Test Cookies"
        assert breakdown[0]["actual_cost"] == Decimal("0")
        assert breakdown[0]["batches_produced"] == 0
        # Variance is -planned (over budget by nothing spent)
        assert breakdown[0]["variance"] == -breakdown[0]["planned_cost"]

    def test_cost_breakdown_with_production(self, test_db, setup_package_status_test_data):
        """Test: Shows actual costs after production."""
        data = setup_package_status_test_data

        _create_production_record(
            event_id=data["event"].id,
            recipe_id=data["recipe"].id,
            batches=1,
        )

        with session_scope() as session:
            breakdown = get_recipe_cost_breakdown(data["event"].id, session=session)

        assert breakdown[0]["actual_cost"] > Decimal("0")
        assert breakdown[0]["batches_produced"] == 1
        # Check variance is calculated
        assert "variance" in breakdown[0]
        assert "variance_percent" in breakdown[0]
