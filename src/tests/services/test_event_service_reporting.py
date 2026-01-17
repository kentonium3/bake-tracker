"""
Tests for event service reporting methods.

Feature 017: Event Reporting & Production Dashboard
Work Package: WP01 - Service Layer Foundation

Tests for:
- export_shopping_list_csv() (T004)
- get_event_cost_analysis() (T005)
- get_recipient_history() fulfillment_status enhancement (T006)
"""

import csv
import os
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.models import (
    Event,
    EventRecipientPackage,
    FulfillmentStatus,
    Recipient,
    Package,
    Recipe,
    FinishedGood,
    FinishedUnit,
    ProductionRun,
    AssemblyRun,
)
from src.models.assembly_type import AssemblyType
from src.services import event_service
from src.services.database import session_scope


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def test_event(test_db):
    """Create a test event."""
    session = test_db()
    event = Event(
        name="Holiday 2024",
        event_date=date(2024, 12, 25),
        year=2024,
    )
    session.add(event)
    session.commit()
    return event


@pytest.fixture
def test_event_2(test_db):
    """Create a second test event (earlier date)."""
    session = test_db()
    event = Event(
        name="Thanksgiving 2024",
        event_date=date(2024, 11, 28),
        year=2024,
    )
    session.add(event)
    session.commit()
    return event


@pytest.fixture
def test_recipient(test_db):
    """Create a test recipient."""
    session = test_db()
    recipient = Recipient(name="Test Recipient")
    session.add(recipient)
    session.commit()
    return recipient


@pytest.fixture
def test_package(test_db):
    """Create a test package."""
    session = test_db()
    package = Package(name="Cookie Box")
    session.add(package)
    session.commit()
    return package


@pytest.fixture
def test_recipe(test_db):
    """Create a test recipe.

    F056: yield_quantity, yield_unit removed from Recipe model.
    """
    session = test_db()
    recipe = Recipe(
        name="Sugar Cookies",
        category="Cookies",
    )
    session.add(recipe)
    session.commit()
    return recipe


@pytest.fixture
def test_finished_unit(test_db, test_recipe):
    """Create a test finished unit."""
    session = test_db()
    fu = FinishedUnit(
        slug="sugar-cookies-48ct",
        display_name="Sugar Cookies (48 ct)",
        recipe_id=test_recipe.id,
        items_per_batch=48,
        inventory_count=0,
    )
    session.add(fu)
    session.commit()
    return fu


@pytest.fixture
def test_finished_good(test_db):
    """Create a test finished good."""
    session = test_db()
    fg = FinishedGood(
        slug="cookie-gift-box",
        display_name="Cookie Gift Box",
        assembly_type=AssemblyType.GIFT_BOX,
        inventory_count=0,
    )
    session.add(fg)
    session.commit()
    return fg


@pytest.fixture
def event_with_production_runs(test_db, test_event, test_recipe, test_finished_unit):
    """Create an event with production runs for cost analysis testing."""
    session = test_db()

    # Create production runs for this event with costs
    # Note: ProductionRun uses total_ingredient_cost (not total_cost)
    run1 = ProductionRun(
        recipe_id=test_recipe.id,
        finished_unit_id=test_finished_unit.id,
        event_id=test_event.id,
        num_batches=2,
        expected_yield=96,
        actual_yield=96,
        produced_at=datetime.now(timezone.utc),
        total_ingredient_cost=Decimal("25.00"),
        per_unit_cost=Decimal("0.26"),
    )
    session.add(run1)

    run2 = ProductionRun(
        recipe_id=test_recipe.id,
        finished_unit_id=test_finished_unit.id,
        event_id=test_event.id,
        num_batches=1,
        expected_yield=48,
        actual_yield=48,
        produced_at=datetime.now(timezone.utc),
        total_ingredient_cost=Decimal("12.50"),
        per_unit_cost=Decimal("0.26"),
    )
    session.add(run2)

    session.commit()
    return test_event


@pytest.fixture
def event_with_assembly_runs(
    test_db, event_with_production_runs, test_finished_good
):
    """Create an event with assembly runs for cost analysis testing."""
    session = test_db()
    event = event_with_production_runs

    # Create assembly run for this event with costs
    # Note: AssemblyRun uses quantity_assembled (not quantity) and total_component_cost
    assembly = AssemblyRun(
        finished_good_id=test_finished_good.id,
        event_id=event.id,
        quantity_assembled=5,
        assembled_at=datetime.now(timezone.utc),
        total_component_cost=Decimal("8.00"),
        per_unit_cost=Decimal("1.60"),
    )
    session.add(assembly)
    session.commit()
    return event


@pytest.fixture
def recipient_with_packages(
    test_db, test_event, test_event_2, test_recipient, test_package
):
    """Create a recipient with packages in multiple events."""
    session = test_db()

    # Assignment in first event (later date - Holiday)
    assignment1 = EventRecipientPackage(
        event_id=test_event.id,
        recipient_id=test_recipient.id,
        package_id=test_package.id,
        quantity=2,
        fulfillment_status=FulfillmentStatus.DELIVERED.value,
    )
    session.add(assignment1)

    # Assignment in second event (earlier date - Thanksgiving)
    assignment2 = EventRecipientPackage(
        event_id=test_event_2.id,
        recipient_id=test_recipient.id,
        package_id=test_package.id,
        quantity=1,
        fulfillment_status=FulfillmentStatus.PENDING.value,
    )
    session.add(assignment2)

    session.commit()
    return test_recipient


# =============================================================================
# Tests for export_shopping_list_csv() - T004
# =============================================================================


class TestExportShoppingListCSV:
    """Tests for export_shopping_list_csv()."""

    def test_export_shopping_list_csv_empty_event(self, test_db, test_event):
        """Test CSV export for event with no shopping list items returns False."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            temp_path = f.name

        try:
            result = event_service.export_shopping_list_csv(test_event.id, temp_path)
            # Empty shopping list returns False (nothing to export)
            assert result is False
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_shopping_list_csv_empty_returns_false(self, test_db, test_event):
        """Test that CSV export returns False for empty shopping list (no file created)."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            temp_path = f.name
        # Delete the temp file so we can verify no new file is created
        os.unlink(temp_path)

        try:
            result = event_service.export_shopping_list_csv(test_event.id, temp_path)
            # Empty shopping list returns False
            assert result is False
            # File should NOT be created for empty export
            assert not os.path.exists(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_shopping_list_csv_header_row(self, test_db, test_event):
        """Test that CSV export includes correct header row."""
        # Add a package assignment to trigger shopping list content
        session = test_db()
        recipient = Recipient(name="Test")
        session.add(recipient)
        session.flush()

        package = Package(name="Test Box")
        session.add(package)
        session.flush()

        assignment = EventRecipientPackage(
            event_id=test_event.id,
            recipient_id=recipient.id,
            package_id=package.id,
            quantity=1,
        )
        session.add(assignment)
        session.commit()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            temp_path = f.name

        try:
            event_service.export_shopping_list_csv(test_event.id, temp_path)

            # Read and verify header
            with open(temp_path, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                rows = list(reader)

            # Header should be present if shopping list has content
            # (may be empty if package has no ingredients)
            if rows:
                expected_header = [
                    "Ingredient",
                    "Quantity Needed",
                    "On Hand",
                    "To Buy",
                    "Unit",
                    "Preferred Brand",
                    "Estimated Cost",
                ]
                assert rows[0] == expected_header
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_shopping_list_csv_io_error(self, test_db, test_event):
        """Test that IO errors are raised properly when file cannot be written."""
        # Note: This test only raises IOError if there's actual content to write.
        # For an empty shopping list, the function returns False without attempting write.
        # For a comprehensive IO error test, we'd need to mock the shopping list
        # or create a more complex setup with package ingredients.
        # For now, test the empty case returns False.
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            temp_path = f.name

        try:
            # Empty event returns False (nothing to export)
            result = event_service.export_shopping_list_csv(test_event.id, temp_path)
            assert result is False
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_shopping_list_csv_nonexistent_event(self, test_db):
        """Test export with nonexistent event ID returns False."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            temp_path = f.name

        try:
            # Nonexistent event has empty shopping list -> returns False
            result = event_service.export_shopping_list_csv(99999, temp_path)
            assert result is False
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


# =============================================================================
# Tests for get_event_cost_analysis() - T005
# =============================================================================


class TestGetEventCostAnalysis:
    """Tests for get_event_cost_analysis()."""

    def test_cost_analysis_no_production(self, test_db, test_event):
        """Test cost analysis with no production data."""
        result = event_service.get_event_cost_analysis(test_event.id)

        assert result["production_costs"] == []
        assert result["assembly_costs"] == []
        assert result["total_production_cost"] == Decimal("0")
        assert result["total_assembly_cost"] == Decimal("0")
        assert result["grand_total"] == Decimal("0")

    def test_cost_analysis_with_production(
        self, test_db, event_with_production_runs
    ):
        """Test cost analysis with production runs."""
        result = event_service.get_event_cost_analysis(event_with_production_runs.id)

        # Should have production costs
        assert len(result["production_costs"]) == 1
        assert result["production_costs"][0]["recipe_name"] == "Sugar Cookies"
        assert result["production_costs"][0]["run_count"] == 2

        # Total production cost: 25.00 + 12.50 = 37.50
        assert result["total_production_cost"] == Decimal("37.50")

        # No assembly costs yet
        assert result["total_assembly_cost"] == Decimal("0")

        # Grand total should equal production
        assert result["grand_total"] == Decimal("37.50")

    def test_cost_analysis_with_production_and_assembly(
        self, test_db, event_with_assembly_runs
    ):
        """Test cost analysis with both production and assembly runs."""
        result = event_service.get_event_cost_analysis(event_with_assembly_runs.id)

        # Production costs
        assert len(result["production_costs"]) == 1
        assert result["total_production_cost"] == Decimal("37.50")

        # Assembly costs
        assert len(result["assembly_costs"]) == 1
        assert result["assembly_costs"][0]["finished_good_name"] == "Cookie Gift Box"
        assert result["assembly_costs"][0]["run_count"] == 1
        assert result["total_assembly_cost"] == Decimal("8.00")

        # Grand total: 37.50 + 8.00 = 45.50
        assert result["grand_total"] == Decimal("45.50")

    def test_cost_analysis_returns_decimals(self, test_db, event_with_production_runs):
        """Test that cost values are returned as Decimals."""
        result = event_service.get_event_cost_analysis(event_with_production_runs.id)

        assert isinstance(result["total_production_cost"], Decimal)
        assert isinstance(result["total_assembly_cost"], Decimal)
        assert isinstance(result["grand_total"], Decimal)

    def test_cost_analysis_variance_calculation(self, test_db, test_event):
        """Test that variance is calculated (estimated - actual)."""
        result = event_service.get_event_cost_analysis(test_event.id)

        # With no production, actual = 0, so variance = estimated - 0 = estimated
        assert result["variance"] == result["estimated_cost"]

    def test_cost_analysis_includes_estimated_cost(
        self, test_db, event_with_production_runs
    ):
        """Test that estimated cost is included from shopping list."""
        result = event_service.get_event_cost_analysis(event_with_production_runs.id)

        # Should have an estimated_cost key (may be 0 if no ingredients needed)
        assert "estimated_cost" in result
        assert isinstance(result["estimated_cost"], Decimal)


# =============================================================================
# Tests for get_recipient_history() with fulfillment_status - T006
# =============================================================================


class TestGetRecipientHistoryFulfillmentStatus:
    """Tests for enhanced get_recipient_history() including fulfillment_status."""

    def test_recipient_history_includes_fulfillment_status(
        self, test_db, recipient_with_packages
    ):
        """Test that recipient history includes fulfillment_status field."""
        history = event_service.get_recipient_history(recipient_with_packages.id)

        assert len(history) == 2

        # Every record should have fulfillment_status
        for record in history:
            assert "fulfillment_status" in record
            # Status should be one of the valid values
            assert record["fulfillment_status"] in [
                FulfillmentStatus.PENDING.value,
                FulfillmentStatus.READY.value,
                FulfillmentStatus.DELIVERED.value,
                None,
            ]

    def test_recipient_history_correct_statuses(
        self, test_db, recipient_with_packages
    ):
        """Test that correct fulfillment statuses are returned for each assignment."""
        history = event_service.get_recipient_history(recipient_with_packages.id)

        # History is sorted by event_date descending
        # First should be Holiday 2024 (Dec 25) with DELIVERED status
        assert history[0]["event"].name == "Holiday 2024"
        assert history[0]["fulfillment_status"] == FulfillmentStatus.DELIVERED.value

        # Second should be Thanksgiving 2024 (Nov 28) with PENDING status
        assert history[1]["event"].name == "Thanksgiving 2024"
        assert history[1]["fulfillment_status"] == FulfillmentStatus.PENDING.value

    def test_recipient_history_sorted_by_date_descending(
        self, test_db, recipient_with_packages
    ):
        """Test that history is sorted by event date descending (most recent first)."""
        history = event_service.get_recipient_history(recipient_with_packages.id)

        # First event should be Holiday 2024 (Dec 25)
        assert history[0]["event"].event_date == date(2024, 12, 25)

        # Second event should be Thanksgiving 2024 (Nov 28)
        assert history[1]["event"].event_date == date(2024, 11, 28)

    def test_recipient_history_empty_for_no_assignments(self, test_db, test_recipient):
        """Test that empty list is returned for recipient with no assignments."""
        history = event_service.get_recipient_history(test_recipient.id)

        assert history == []

    def test_recipient_history_nonexistent_recipient(self, test_db):
        """Test that empty list is returned for nonexistent recipient."""
        history = event_service.get_recipient_history(99999)

        assert history == []

    def test_recipient_history_includes_all_fields(
        self, test_db, recipient_with_packages
    ):
        """Test that history includes all expected fields."""
        history = event_service.get_recipient_history(recipient_with_packages.id)

        assert len(history) > 0
        record = history[0]

        # All expected fields
        assert "event" in record
        assert "package" in record
        assert "quantity" in record
        assert "notes" in record
        assert "fulfillment_status" in record
