"""
Integration tests for Event Planning Workflow (Feature 006).

Tests cover:
- T067: Full gift planning workflow end-to-end
- T068: FIFO cost accuracy (SC-002)
- T069: Shopping list shortfall accuracy (SC-003)
- T070: Performance testing (<2s for 50 assignments) (SC-004)
- T071: Edge case testing
"""

import pytest
import time
from datetime import date
from decimal import Decimal

from src.services import (
    # Package services
    create_package,
    get_package_by_id,
    add_finished_good_to_package,
    calculate_package_cost,
    delete_package,
    # Event services
    create_event,
    get_event_by_id,
    get_all_events,
    get_events_by_year,
    assign_package_to_recipient,
    remove_assignment,
    get_event_assignments,
    get_event_summary,
    get_recipe_needs,
    get_shopping_list,
    delete_event,
    # Recipient services
    create_recipient,
    get_recipient,
    delete_recipient,
    check_recipient_has_assignments,
)
from src.services.database import session_scope
from src.services.exceptions import ValidationError
from src.services.database import session_scope
from src.models import (
    Package,
    PackageFinishedGood,
    Event,
    EventRecipientPackage,
    Recipient,
    FinishedGood,
    FinishedUnit,
    Recipe,
    Ingredient,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_recipe(test_db):
    """Create a sample recipe for testing."""
    from src.models import Recipe

    # F056: yield_quantity, yield_unit removed from Recipe model
    session = test_db()

    recipe = Recipe(
        name="Test Cookies",
        category="Cookies",
        notes="Test recipe",
    )
    session.add(recipe)
    session.commit()
    session.refresh(recipe)
    return recipe


@pytest.fixture
def sample_finished_unit(test_db, sample_recipe):
    """Create a sample finished unit."""
    from src.models.finished_unit import YieldMode

    session = test_db()

    fu = FinishedUnit(
        display_name="Test Cookie Unit",
        slug="test-cookie-unit",
        recipe_id=sample_recipe.id,
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=24,
    )
    session.add(fu)
    session.commit()
    session.refresh(fu)
    return fu


@pytest.fixture
def sample_finished_good(test_db, sample_finished_unit):
    """Create a sample finished good (assembly)."""
    from src.models.assembly_type import AssemblyType

    session = test_db()

    fg = FinishedGood(
        display_name="Cookie Box",
        slug="cookie-box",
        assembly_type=AssemblyType.CUSTOM_ORDER,
    )
    session.add(fg)
    session.commit()
    session.refresh(fg)
    return fg


@pytest.fixture
def sample_package(test_db, sample_finished_good):
    """Create a sample package with finished goods."""
    from src.services import add_finished_good_to_package

    package = create_package(
        {
            "name": "Test Gift Package",
            "description": "A test package",
            "is_template": False,
        }
    )

    # Add finished good to package using service
    add_finished_good_to_package(
        package_id=package.id,
        finished_good_id=sample_finished_good.id,
        quantity=2,
    )

    # Re-fetch package to get updated data
    return get_package_by_id(package.id)


@pytest.fixture
def sample_recipient(test_db):
    """Create a sample recipient."""
    return create_recipient(
        {"name": "Test Recipient", "household_name": "Test Family", "address": "123 Test St"}
    )


@pytest.fixture
def sample_event(test_db):
    """Create a sample event."""
    with session_scope() as session:
        return create_event(
            name="Test Holiday Event",
            event_date=date(2024, 12, 25),
            year=2024,
            notes="Test event",
            session=session,
        )


@pytest.fixture
def sample_event_with_assignment(test_db, sample_event, sample_recipient, sample_package):
    """Create an event with a recipient-package assignment."""
    with session_scope() as session:
        assignment = assign_package_to_recipient(
            event_id=sample_event.id,
            recipient_id=sample_recipient.id,
            package_id=sample_package.id,
            quantity=1,
            session=session,
        )
    return sample_event, sample_recipient, sample_package, assignment


# ============================================================================
# T067 - Full Gift Planning Workflow Tests
# ============================================================================


class TestFullWorkflow:
    """Integration tests for the complete gift planning workflow."""

    def test_full_gift_planning_workflow(self, test_db, sample_finished_good, sample_recipe):
        """
        Test complete gift planning workflow from package creation to event summary.

        Steps:
        1. Create package with FinishedGoods
        2. Create recipient
        3. Create event
        4. Assign package to recipient
        5. Verify event summary
        """
        # Step 1: Create package
        package = create_package(
            {
                "name": "Holiday Gift Box",
                "description": "Deluxe cookie assortment",
                "is_template": False,
            }
        )
        assert package is not None
        assert package.id is not None

        # Add finished good to package using service
        add_finished_good_to_package(
            package_id=package.id,
            finished_good_id=sample_finished_good.id,
            quantity=3,
        )
        # Re-fetch package
        package = get_package_by_id(package.id)

        # Step 2: Create recipient
        recipient = create_recipient({"name": "John Smith", "household_name": "Smith Family"})
        assert recipient is not None
        assert recipient.id is not None

        # Step 3: Create event
        with session_scope() as session:
            event = create_event(
                name="Christmas 2024",
                event_date=date(2024, 12, 25),
                year=2024,
                session=session,
            )
        assert event is not None
        assert event.id is not None

        # Step 4: Assign package to recipient
        with session_scope() as session:
            assignment = assign_package_to_recipient(
                event_id=event.id,
                recipient_id=recipient.id,
                package_id=package.id,
                quantity=1,
                session=session,
            )
        assert assignment is not None

        # Step 5: Verify event summary
        with session_scope() as session:
            summary = get_event_summary(event.id, session=session)
        assert summary is not None
        assert summary["recipient_count"] == 1
        assert summary["assignment_count"] == 1
        assert "total_cost" in summary

    def test_workflow_multiple_recipients(self, test_db, sample_package):
        """Test workflow with multiple recipients."""
        # Create multiple recipients
        recipients = []
        for i in range(3):
            r = create_recipient({"name": f"Recipient {i+1}"})
            recipients.append(r)

        # Create event
        with session_scope() as session:
            event = create_event(
                name="Multi-Recipient Event",
                event_date=date(2024, 12, 25),
                year=2024,
                session=session,
            )

        # Assign package to all recipients
        with session_scope() as session:
            for recipient in recipients:
                assign_package_to_recipient(
                    event_id=event.id,
                    recipient_id=recipient.id,
                    package_id=sample_package.id,
                    quantity=1,
                    session=session,
                )

        # Verify summary
        with session_scope() as session:
            summary = get_event_summary(event.id, session=session)
        assert summary["recipient_count"] == 3
        assert summary["assignment_count"] == 3

    def test_workflow_crud_preserves_integrity(self, test_db, sample_event_with_assignment):
        """Test that CRUD operations preserve data integrity."""
        event, recipient, package, assignment = sample_event_with_assignment

        # Verify initial state
        assert check_recipient_has_assignments(recipient.id) is True

        # Remove assignment
        with session_scope() as session:
            remove_assignment(assignment.id, session=session)

        # Verify assignment is gone
        assert check_recipient_has_assignments(recipient.id) is False

        # Event and recipient should still exist
        with session_scope() as session:
            retrieved_event = get_event_by_id(event.id, session=session)
        assert retrieved_event is not None

        retrieved_recipient = get_recipient(recipient.id)
        assert retrieved_recipient is not None


# ============================================================================
# T068 - FIFO Cost Accuracy Tests (SC-002)
# ============================================================================


class TestFIFOCostAccuracy:
    """Tests for FIFO cost calculation accuracy."""

    def test_package_cost_calculation(self, test_db, sample_package, sample_finished_good):
        """Test that package costs return zero for definitions.

        Feature 045: Costs are now tracked on production/assembly instances,
        not on definition models. Package definition cost returns Decimal("0.00").
        """
        cost = calculate_package_cost(sample_package.id)
        assert cost is not None
        assert cost == Decimal("0.00")

    def test_event_total_cost_matches_package_cost(self, test_db, sample_event_with_assignment):
        """Test that event total cost equals sum of package costs.

        Feature 045: Costs are now tracked on production/assembly instances,
        not on definition models. Both package and event costs return Decimal("0.00").
        """
        event, recipient, package, assignment = sample_event_with_assignment

        # Get package cost - returns 0.00 per Feature 045
        package_cost = calculate_package_cost(package.id)
        assert package_cost == Decimal("0.00")

        # Get event summary
        with session_scope() as session:
            summary = get_event_summary(event.id, session=session)

        # Event cost should equal package cost (both 0.00 for definitions)
        # Note: summary["total_cost"] is returned as string by get_event_summary()
        assert summary["total_cost"] == "0.00"

    def test_cost_with_multiple_assignments(self, test_db, sample_package):
        """Test cost calculation with multiple assignments.

        Feature 045: Costs are now tracked on production/assembly instances,
        not on definition models. All definition costs return Decimal("0.00").
        """
        # Create event and recipients
        with session_scope() as session:
            event = create_event(
                name="Multi-Assignment Event",
                event_date=date(2024, 12, 25),
                year=2024,
                session=session,
            )

        r1 = create_recipient({"name": "Recipient 1"})
        r2 = create_recipient({"name": "Recipient 2"})

        # Assign package with different quantities
        with session_scope() as session:
            assign_package_to_recipient(event.id, r1.id, sample_package.id, quantity=1, session=session)
            assign_package_to_recipient(event.id, r2.id, sample_package.id, quantity=2, session=session)

        # Get package cost - returns 0.00 per Feature 045
        package_cost = calculate_package_cost(sample_package.id)
        assert package_cost == Decimal("0.00")

        with session_scope() as session:
            summary = get_event_summary(event.id, session=session)
        # Event cost is 0.00 for definitions
        assert summary["total_cost"] == "0.00"

    def test_cost_returns_zero_for_definitions(self, test_db, sample_finished_good):
        """Test that definition-level costs return zero.

        Feature 045: Costs are now tracked on production/assembly instances,
        not on definition models. This test verifies the new behavior.
        """
        session = test_db()

        # Create package with finished good
        package = create_package({"name": "Precision Test Package"})
        pfg = PackageFinishedGood(
            package_id=package.id,
            finished_good_id=sample_finished_good.id,
            quantity=3,
        )
        session.add(pfg)
        session.commit()

        # Package cost is 0.00 per Feature 045 (costs on instances, not definitions)
        cost = calculate_package_cost(package.id)
        assert cost == Decimal("0.00")


# ============================================================================
# T069 - Shopping List Shortfall Accuracy (SC-003)
# ============================================================================


class TestShoppingListAccuracy:
    """Tests for shopping list shortfall calculations."""

    def test_shopping_list_basic(self, test_db, sample_event_with_assignment):
        """Test basic shopping list generation."""
        event, _, _, _ = sample_event_with_assignment

        # Get shopping list - may be empty if no recipe ingredients
        with session_scope() as session:
            shopping = get_shopping_list(event.id, session=session)

        # Feature 007: Now returns dict with 'items' key
        assert isinstance(shopping, dict)
        assert "items" in shopping
        assert "total_estimated_cost" in shopping
        assert "items_count" in shopping
        assert "items_with_shortfall" in shopping
        assert isinstance(shopping["items"], list)

    def test_shopping_list_empty_event(self, test_db, sample_event):
        """Test shopping list for event with no assignments."""
        with session_scope() as session:
            shopping = get_shopping_list(sample_event.id, session=session)

        # Feature 007: Returns dict with empty items list
        assert isinstance(shopping, dict)
        assert shopping["items"] == []
        assert shopping["items_count"] == 0


# ============================================================================
# T070 - Performance Tests (SC-004)
# ============================================================================


class TestPerformance:
    """Performance tests for <2s load time with 50 assignments."""

    def test_event_summary_performance(self, test_db, sample_package):
        """Test that event summary loads in <2s with many assignments."""
        # Create event
        with session_scope() as session:
            event = create_event(
                name="Performance Test Event",
                event_date=date(2024, 12, 25),
                year=2024,
                session=session,
            )
            event_id = event.id

        # Create 50 recipients and assignments
        with session_scope() as session:
            for i in range(50):
                recipient = create_recipient({"name": f"Recipient {i+1}"})
                assign_package_to_recipient(
                    event_id=event_id,
                    recipient_id=recipient.id,
                    package_id=sample_package.id,
                    quantity=1,
                    session=session,
                )

        # Measure summary load time
        start = time.time()
        with session_scope() as session:
            summary = get_event_summary(event_id, session=session)
        elapsed = time.time() - start

        assert elapsed < 2.0, f"Summary took {elapsed:.2f}s (>2s limit)"
        assert summary["assignment_count"] == 50

    def test_recipe_needs_performance(self, test_db, sample_package):
        """Test that recipe needs loads in <2s with many assignments."""
        with session_scope() as session:
            event = create_event(
                name="Recipe Needs Perf Test",
                event_date=date(2024, 12, 25),
                year=2024,
                session=session,
            )
            event_id = event.id

        # Create 50 assignments
        with session_scope() as session:
            for i in range(50):
                recipient = create_recipient({"name": f"Recipient R{i+1}"})
                assign_package_to_recipient(
                    event_id=event_id,
                    recipient_id=recipient.id,
                    package_id=sample_package.id,
                    quantity=1,
                    session=session,
                )

        # Measure recipe needs load time
        start = time.time()
        with session_scope() as session:
            needs = get_recipe_needs(event_id, session=session)
        elapsed = time.time() - start

        assert elapsed < 2.0, f"Recipe needs took {elapsed:.2f}s (>2s limit)"

    def test_shopping_list_performance(self, test_db, sample_package):
        """Test that shopping list loads in <2s with many assignments."""
        with session_scope() as session:
            event = create_event(
                name="Shopping List Perf Test",
                event_date=date(2024, 12, 25),
                year=2024,
                session=session,
            )
            event_id = event.id

        # Create 50 assignments
        with session_scope() as session:
            for i in range(50):
                recipient = create_recipient({"name": f"Recipient S{i+1}"})
                assign_package_to_recipient(
                    event_id=event_id,
                    recipient_id=recipient.id,
                    package_id=sample_package.id,
                    quantity=1,
                    session=session,
                )

        # Measure shopping list load time
        start = time.time()
        with session_scope() as session:
            shopping = get_shopping_list(event_id, session=session)
        elapsed = time.time() - start

        assert elapsed < 2.0, f"Shopping list took {elapsed:.2f}s (>2s limit)"


# ============================================================================
# T071 - Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_empty_package(self, test_db):
        """Test package with no finished goods."""
        package = create_package({"name": "Empty Package", "description": "No contents"})

        # Cost should be 0
        cost = calculate_package_cost(package.id)
        assert cost == Decimal("0.00")

    def test_event_with_no_assignments(self, test_db, sample_event):
        """Test event summary with no assignments."""
        with session_scope() as session:
            summary = get_event_summary(sample_event.id, session=session)

        assert summary["assignment_count"] == 0
        assert summary["recipient_count"] == 0
        assert summary["total_cost"] == "0.00"

    def test_finished_good_in_package(self, test_db):
        """Test that finished goods can be added to packages.

        Feature 045: Costs are now tracked on production/assembly instances,
        not on definition models. FinishedGood no longer has total_cost field.
        """
        from src.models.assembly_type import AssemblyType

        session = test_db()

        # Create FG (no cost field per Feature 045)
        fg = FinishedGood(
            display_name="Test Item",
            slug="test-item",
            assembly_type=AssemblyType.CUSTOM_ORDER,
        )
        session.add(fg)
        session.commit()
        session.refresh(fg)

        # Create package with this FG
        package = create_package({"name": "Test Package"})
        pfg = PackageFinishedGood(
            package_id=package.id,
            finished_good_id=fg.id,
            quantity=1,
        )
        session.add(pfg)
        session.commit()

        # Package cost is 0.00 per Feature 045 (costs on instances, not definitions)
        cost = calculate_package_cost(package.id)
        assert cost == Decimal("0.00")

    def test_event_year_filtering(self, test_db):
        """Test filtering events by year."""
        # Create events in different years
        with session_scope() as session:
            event_2023 = create_event(
                name="Event 2023",
                event_date=date(2023, 12, 25),
                year=2023,
                session=session,
            )
            event_2024 = create_event(
                name="Event 2024",
                event_date=date(2024, 12, 25),
                year=2024,
                session=session,
            )

        # Filter by year
        with session_scope() as session:
            events_2024 = get_events_by_year(2024, session=session)
            events_2023 = get_events_by_year(2023, session=session)

            assert len(events_2024) >= 1
            assert len(events_2023) >= 1
            assert all(e.year == 2024 for e in events_2024)
            assert all(e.year == 2023 for e in events_2023)

    def test_cascade_delete_event(self, test_db, sample_event_with_assignment):
        """Test that deleting event cascades to assignments."""
        event, recipient, package, assignment = sample_event_with_assignment
        event_id = event.id

        # Delete event with cascade
        with session_scope() as session:
            delete_event(event_id, cascade_assignments=True, session=session)

        # Event should be gone (returns None, doesn't raise)
        with session_scope() as session:
            deleted_event = get_event_by_id(event_id, session=session)
        assert deleted_event is None

        # Recipient should still exist
        retrieved = get_recipient(recipient.id)
        assert retrieved is not None

    def test_validation_errors(self, test_db):
        """Test that validation errors are raised appropriately."""
        # Empty name should fail
        with pytest.raises(ValidationError):
            create_package({"name": ""})

        with pytest.raises(ValidationError):
            create_recipient({"name": ""})

        with pytest.raises(ValidationError):
            with session_scope() as session:
                create_event(
                    name="",
                    event_date=date(2024, 12, 25),
                    year=2024,
                    session=session,
                )
