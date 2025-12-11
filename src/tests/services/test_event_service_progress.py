"""
Tests for event service progress calculation.

Feature 016: Event-Centric Production Model
Tests for production/assembly progress and overall event progress.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal

from src.models import (
    Event,
    Recipe,
    FinishedGood,
    FinishedUnit,
    EventProductionTarget,
    EventAssemblyTarget,
    ProductionRun,
    AssemblyRun,
    EventRecipientPackage,
    Recipient,
    Package,
    FulfillmentStatus,
)
from src.models.assembly_type import AssemblyType
from src.services import event_service
from src.services.database import session_scope


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def event_christmas(test_db):
    """Create a Christmas 2024 event for testing."""
    session = test_db()
    event = Event(
        name="Christmas 2024",
        event_date=date(2024, 12, 25),
        year=2024,
    )
    session.add(event)
    session.commit()
    return event


@pytest.fixture
def event_thanksgiving(test_db):
    """Create a Thanksgiving 2024 event for testing."""
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
def recipe_cookies(test_db):
    """Create a cookie recipe for testing."""
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
def recipe_brownies(test_db):
    """Create a brownie recipe for testing."""
    session = test_db()
    recipe = Recipe(
        name="Fudge Brownies",
        category="Brownies",
        yield_quantity=24.0,
        yield_unit="brownies",
    )
    session.add(recipe)
    session.commit()
    return recipe


@pytest.fixture
def finished_unit_cookies(test_db, recipe_cookies):
    """Create a finished unit for cookies."""
    session = test_db()
    fu = FinishedUnit(
        slug="sugar-cookies-48ct",
        display_name="Sugar Cookies (48 ct)",
        recipe_id=recipe_cookies.id,
        items_per_batch=48,
        inventory_count=0,
    )
    session.add(fu)
    session.commit()
    return fu


@pytest.fixture
def finished_good_gift_box(test_db):
    """Create a gift box finished good for testing."""
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
def finished_good_tray(test_db):
    """Create a tray finished good for testing."""
    session = test_db()
    fg = FinishedGood(
        slug="cookie-tray",
        display_name="Cookie Tray",
        assembly_type=AssemblyType.VARIETY_PACK,
        inventory_count=0,
    )
    session.add(fg)
    session.commit()
    return fg


@pytest.fixture
def recipient(test_db):
    """Create a recipient for testing."""
    session = test_db()
    r = Recipient(name="Test Recipient")
    session.add(r)
    session.commit()
    return r


@pytest.fixture
def package(test_db):
    """Create a package for testing."""
    session = test_db()
    p = Package(name="Test Package")
    session.add(p)
    session.commit()
    return p


# =============================================================================
# Tests for Production Progress
# =============================================================================


class TestProductionProgress:
    """Tests for get_production_progress() function."""

    def test_progress_zero_percent(self, test_db, event_christmas, recipe_cookies):
        """0% when no production recorded for target."""
        # Set target but no production
        event_service.set_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_cookies.id,
            target_batches=4,
        )

        result = event_service.get_production_progress(event_christmas.id)

        assert len(result) == 1
        assert result[0]["produced_batches"] == 0
        assert result[0]["progress_pct"] == 0.0
        assert result[0]["is_complete"] is False

    def test_progress_fifty_percent(
        self, test_db, event_christmas, recipe_cookies, finished_unit_cookies
    ):
        """50% when half of target produced."""
        # Set target=4 batches
        event_service.set_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_cookies.id,
            target_batches=4,
        )

        # Record 2 batches for this event
        with session_scope() as session:
            run = ProductionRun(
                recipe_id=recipe_cookies.id,
                finished_unit_id=finished_unit_cookies.id,
                event_id=event_christmas.id,
                num_batches=2,
                expected_yield=96,
                actual_yield=96,
                produced_at=datetime.utcnow(),
                total_ingredient_cost=Decimal("10.00"),
                per_unit_cost=Decimal("0.10"),
            )
            session.add(run)
            session.commit()

        result = event_service.get_production_progress(event_christmas.id)

        assert len(result) == 1
        assert result[0]["produced_batches"] == 2
        assert result[0]["progress_pct"] == 50.0
        assert result[0]["is_complete"] is False

    def test_progress_one_hundred_percent(
        self, test_db, event_christmas, recipe_cookies, finished_unit_cookies
    ):
        """100% when target exactly met."""
        event_service.set_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_cookies.id,
            target_batches=4,
        )

        with session_scope() as session:
            run = ProductionRun(
                recipe_id=recipe_cookies.id,
                finished_unit_id=finished_unit_cookies.id,
                event_id=event_christmas.id,
                num_batches=4,
                expected_yield=192,
                actual_yield=192,
                produced_at=datetime.utcnow(),
                total_ingredient_cost=Decimal("20.00"),
                per_unit_cost=Decimal("0.10"),
            )
            session.add(run)
            session.commit()

        result = event_service.get_production_progress(event_christmas.id)

        assert len(result) == 1
        assert result[0]["produced_batches"] == 4
        assert result[0]["progress_pct"] == 100.0
        assert result[0]["is_complete"] is True

    def test_progress_over_hundred_percent(
        self, test_db, event_christmas, recipe_cookies, finished_unit_cookies
    ):
        """125% when over-produced."""
        event_service.set_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_cookies.id,
            target_batches=4,
        )

        with session_scope() as session:
            run = ProductionRun(
                recipe_id=recipe_cookies.id,
                finished_unit_id=finished_unit_cookies.id,
                event_id=event_christmas.id,
                num_batches=5,
                expected_yield=240,
                actual_yield=240,
                produced_at=datetime.utcnow(),
                total_ingredient_cost=Decimal("25.00"),
                per_unit_cost=Decimal("0.10"),
            )
            session.add(run)
            session.commit()

        result = event_service.get_production_progress(event_christmas.id)

        assert len(result) == 1
        assert result[0]["produced_batches"] == 5
        assert result[0]["progress_pct"] == 125.0
        assert result[0]["is_complete"] is True

    def test_progress_only_counts_event_runs(
        self, test_db, event_christmas, event_thanksgiving, recipe_cookies, finished_unit_cookies
    ):
        """Only counts runs with matching event_id."""
        event_service.set_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_cookies.id,
            target_batches=4,
        )

        with session_scope() as session:
            # Run for Christmas event
            run1 = ProductionRun(
                recipe_id=recipe_cookies.id,
                finished_unit_id=finished_unit_cookies.id,
                event_id=event_christmas.id,
                num_batches=2,
                expected_yield=96,
                actual_yield=96,
                produced_at=datetime.utcnow(),
                total_ingredient_cost=Decimal("10.00"),
                per_unit_cost=Decimal("0.10"),
            )
            # Run for Thanksgiving event (should not count)
            run2 = ProductionRun(
                recipe_id=recipe_cookies.id,
                finished_unit_id=finished_unit_cookies.id,
                event_id=event_thanksgiving.id,
                num_batches=3,
                expected_yield=144,
                actual_yield=144,
                produced_at=datetime.utcnow(),
                total_ingredient_cost=Decimal("15.00"),
                per_unit_cost=Decimal("0.10"),
            )
            # Standalone run (no event_id, should not count)
            run3 = ProductionRun(
                recipe_id=recipe_cookies.id,
                finished_unit_id=finished_unit_cookies.id,
                event_id=None,
                num_batches=10,
                expected_yield=480,
                actual_yield=480,
                produced_at=datetime.utcnow(),
                total_ingredient_cost=Decimal("50.00"),
                per_unit_cost=Decimal("0.10"),
            )
            session.add_all([run1, run2, run3])
            session.commit()

        result = event_service.get_production_progress(event_christmas.id)

        assert len(result) == 1
        # Only the 2 batches from Christmas event should be counted
        assert result[0]["produced_batches"] == 2
        assert result[0]["progress_pct"] == 50.0

    def test_progress_empty_when_no_targets(self, test_db, event_christmas):
        """Empty list when no targets set."""
        result = event_service.get_production_progress(event_christmas.id)
        assert result == []

    def test_progress_multiple_targets(
        self, test_db, event_christmas, recipe_cookies, recipe_brownies
    ):
        """Returns progress for multiple targets."""
        event_service.set_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_cookies.id,
            target_batches=4,
        )
        event_service.set_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_brownies.id,
            target_batches=2,
        )

        result = event_service.get_production_progress(event_christmas.id)

        assert len(result) == 2


# =============================================================================
# Tests for Assembly Progress
# =============================================================================


class TestAssemblyProgress:
    """Tests for get_assembly_progress() function."""

    def test_progress_zero_percent(
        self, test_db, event_christmas, finished_good_gift_box
    ):
        """0% when no assembly recorded for target."""
        event_service.set_assembly_target(
            event_id=event_christmas.id,
            finished_good_id=finished_good_gift_box.id,
            target_quantity=20,
        )

        result = event_service.get_assembly_progress(event_christmas.id)

        assert len(result) == 1
        assert result[0]["assembled_quantity"] == 0
        assert result[0]["progress_pct"] == 0.0
        assert result[0]["is_complete"] is False

    def test_progress_fifty_percent(
        self, test_db, event_christmas, finished_good_gift_box
    ):
        """50% when half of target assembled."""
        event_service.set_assembly_target(
            event_id=event_christmas.id,
            finished_good_id=finished_good_gift_box.id,
            target_quantity=20,
        )

        with session_scope() as session:
            run = AssemblyRun(
                finished_good_id=finished_good_gift_box.id,
                event_id=event_christmas.id,
                quantity_assembled=10,
                assembled_at=datetime.utcnow(),
                total_component_cost=Decimal("50.00"),
                per_unit_cost=Decimal("5.00"),
            )
            session.add(run)
            session.commit()

        result = event_service.get_assembly_progress(event_christmas.id)

        assert len(result) == 1
        assert result[0]["assembled_quantity"] == 10
        assert result[0]["progress_pct"] == 50.0
        assert result[0]["is_complete"] is False

    def test_progress_one_hundred_percent(
        self, test_db, event_christmas, finished_good_gift_box
    ):
        """100% when target exactly met."""
        event_service.set_assembly_target(
            event_id=event_christmas.id,
            finished_good_id=finished_good_gift_box.id,
            target_quantity=20,
        )

        with session_scope() as session:
            run = AssemblyRun(
                finished_good_id=finished_good_gift_box.id,
                event_id=event_christmas.id,
                quantity_assembled=20,
                assembled_at=datetime.utcnow(),
                total_component_cost=Decimal("100.00"),
                per_unit_cost=Decimal("5.00"),
            )
            session.add(run)
            session.commit()

        result = event_service.get_assembly_progress(event_christmas.id)

        assert len(result) == 1
        assert result[0]["assembled_quantity"] == 20
        assert result[0]["progress_pct"] == 100.0
        assert result[0]["is_complete"] is True

    def test_progress_over_hundred_percent(
        self, test_db, event_christmas, finished_good_gift_box
    ):
        """150% when over-assembled."""
        event_service.set_assembly_target(
            event_id=event_christmas.id,
            finished_good_id=finished_good_gift_box.id,
            target_quantity=20,
        )

        with session_scope() as session:
            run = AssemblyRun(
                finished_good_id=finished_good_gift_box.id,
                event_id=event_christmas.id,
                quantity_assembled=30,
                assembled_at=datetime.utcnow(),
                total_component_cost=Decimal("150.00"),
                per_unit_cost=Decimal("5.00"),
            )
            session.add(run)
            session.commit()

        result = event_service.get_assembly_progress(event_christmas.id)

        assert len(result) == 1
        assert result[0]["assembled_quantity"] == 30
        assert result[0]["progress_pct"] == 150.0
        assert result[0]["is_complete"] is True

    def test_progress_only_counts_event_runs(
        self, test_db, event_christmas, event_thanksgiving, finished_good_gift_box
    ):
        """Only counts runs with matching event_id."""
        event_service.set_assembly_target(
            event_id=event_christmas.id,
            finished_good_id=finished_good_gift_box.id,
            target_quantity=20,
        )

        with session_scope() as session:
            # Run for Christmas event
            run1 = AssemblyRun(
                finished_good_id=finished_good_gift_box.id,
                event_id=event_christmas.id,
                quantity_assembled=5,
                assembled_at=datetime.utcnow(),
                total_component_cost=Decimal("25.00"),
                per_unit_cost=Decimal("5.00"),
            )
            # Run for Thanksgiving (should not count)
            run2 = AssemblyRun(
                finished_good_id=finished_good_gift_box.id,
                event_id=event_thanksgiving.id,
                quantity_assembled=10,
                assembled_at=datetime.utcnow(),
                total_component_cost=Decimal("50.00"),
                per_unit_cost=Decimal("5.00"),
            )
            # Standalone run (no event_id)
            run3 = AssemblyRun(
                finished_good_id=finished_good_gift_box.id,
                event_id=None,
                quantity_assembled=15,
                assembled_at=datetime.utcnow(),
                total_component_cost=Decimal("75.00"),
                per_unit_cost=Decimal("5.00"),
            )
            session.add_all([run1, run2, run3])
            session.commit()

        result = event_service.get_assembly_progress(event_christmas.id)

        assert len(result) == 1
        assert result[0]["assembled_quantity"] == 5
        assert result[0]["progress_pct"] == 25.0

    def test_progress_empty_when_no_targets(self, test_db, event_christmas):
        """Empty list when no targets set."""
        result = event_service.get_assembly_progress(event_christmas.id)
        assert result == []


# =============================================================================
# Tests for Overall Progress
# =============================================================================


class TestOverallProgress:
    """Tests for get_event_overall_progress() function."""

    def test_all_complete_when_no_targets(self, test_db, event_christmas):
        """production_complete and assembly_complete are True when no targets."""
        result = event_service.get_event_overall_progress(event_christmas.id)

        assert result["production_targets_count"] == 0
        assert result["production_complete_count"] == 0
        assert result["production_complete"] is True
        assert result["assembly_targets_count"] == 0
        assert result["assembly_complete_count"] == 0
        assert result["assembly_complete"] is True

    def test_counts_production_complete(
        self, test_db, event_christmas, recipe_cookies, recipe_brownies, finished_unit_cookies
    ):
        """Correctly counts completed production targets."""
        # Create 2 production targets
        event_service.set_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_cookies.id,
            target_batches=2,
        )
        event_service.set_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_brownies.id,
            target_batches=3,
        )

        # Complete only the first one
        with session_scope() as session:
            run = ProductionRun(
                recipe_id=recipe_cookies.id,
                finished_unit_id=finished_unit_cookies.id,
                event_id=event_christmas.id,
                num_batches=2,
                expected_yield=96,
                actual_yield=96,
                produced_at=datetime.utcnow(),
                total_ingredient_cost=Decimal("10.00"),
                per_unit_cost=Decimal("0.10"),
            )
            session.add(run)
            session.commit()

        result = event_service.get_event_overall_progress(event_christmas.id)

        assert result["production_targets_count"] == 2
        assert result["production_complete_count"] == 1
        assert result["production_complete"] is False

    def test_package_counts_by_status(
        self, test_db, event_christmas, recipient, package
    ):
        """Correctly counts packages by fulfillment status."""
        with session_scope() as session:
            # Create 3 packages with different statuses
            p1 = EventRecipientPackage(
                event_id=event_christmas.id,
                recipient_id=recipient.id,
                package_id=package.id,
                quantity=1,
                fulfillment_status=FulfillmentStatus.PENDING.value,
            )
            p2 = EventRecipientPackage(
                event_id=event_christmas.id,
                recipient_id=recipient.id,
                package_id=package.id,
                quantity=1,
                fulfillment_status=FulfillmentStatus.READY.value,
            )
            p3 = EventRecipientPackage(
                event_id=event_christmas.id,
                recipient_id=recipient.id,
                package_id=package.id,
                quantity=1,
                fulfillment_status=FulfillmentStatus.DELIVERED.value,
            )
            session.add_all([p1, p2, p3])
            session.commit()

        result = event_service.get_event_overall_progress(event_christmas.id)

        assert result["packages_pending"] == 1
        assert result["packages_ready"] == 1
        assert result["packages_delivered"] == 1
        assert result["packages_total"] == 3

    def test_mixed_progress(
        self,
        test_db,
        event_christmas,
        recipe_cookies,
        finished_unit_cookies,
        finished_good_gift_box,
        recipient,
        package,
    ):
        """Correctly aggregates all progress metrics."""
        # Production: 1 target, 50% complete
        event_service.set_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_cookies.id,
            target_batches=4,
        )
        with session_scope() as session:
            run = ProductionRun(
                recipe_id=recipe_cookies.id,
                finished_unit_id=finished_unit_cookies.id,
                event_id=event_christmas.id,
                num_batches=2,
                expected_yield=96,
                actual_yield=96,
                produced_at=datetime.utcnow(),
                total_ingredient_cost=Decimal("10.00"),
                per_unit_cost=Decimal("0.10"),
            )
            session.add(run)
            session.commit()

        # Assembly: 1 target, 100% complete
        event_service.set_assembly_target(
            event_id=event_christmas.id,
            finished_good_id=finished_good_gift_box.id,
            target_quantity=10,
        )
        with session_scope() as session:
            run = AssemblyRun(
                finished_good_id=finished_good_gift_box.id,
                event_id=event_christmas.id,
                quantity_assembled=10,
                assembled_at=datetime.utcnow(),
                total_component_cost=Decimal("50.00"),
                per_unit_cost=Decimal("5.00"),
            )
            session.add(run)
            session.commit()

        # Packages: 2 pending
        with session_scope() as session:
            p1 = EventRecipientPackage(
                event_id=event_christmas.id,
                recipient_id=recipient.id,
                package_id=package.id,
                quantity=1,
                fulfillment_status=FulfillmentStatus.PENDING.value,
            )
            p2 = EventRecipientPackage(
                event_id=event_christmas.id,
                recipient_id=recipient.id,
                package_id=package.id,
                quantity=1,
                fulfillment_status=FulfillmentStatus.PENDING.value,
            )
            session.add_all([p1, p2])
            session.commit()

        result = event_service.get_event_overall_progress(event_christmas.id)

        assert result["production_targets_count"] == 1
        assert result["production_complete_count"] == 0
        assert result["production_complete"] is False
        assert result["assembly_targets_count"] == 1
        assert result["assembly_complete_count"] == 1
        assert result["assembly_complete"] is True
        assert result["packages_pending"] == 2
        assert result["packages_ready"] == 0
        assert result["packages_delivered"] == 0
        assert result["packages_total"] == 2
