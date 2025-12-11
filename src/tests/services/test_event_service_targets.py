"""
Tests for event service target CRUD operations.

Feature 016: Event-Centric Production Model
Tests for production/assembly target CRUD methods.
"""

import pytest
from datetime import date
from decimal import Decimal

from src.models import (
    Event,
    Recipe,
    FinishedGood,
    EventProductionTarget,
    EventAssemblyTarget,
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


# =============================================================================
# Tests for Production Targets
# =============================================================================


class TestSetProductionTarget:
    """Tests for set_production_target() function."""

    def test_creates_new_target(self, test_db, event_christmas, recipe_cookies):
        """New target is created when none exists."""
        result = event_service.set_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_cookies.id,
            target_batches=5,
            notes="Make plenty for guests",
        )

        assert result.event_id == event_christmas.id
        assert result.recipe_id == recipe_cookies.id
        assert result.target_batches == 5
        assert result.notes == "Make plenty for guests"

        # Verify in database
        with session_scope() as session:
            db_target = (
                session.query(EventProductionTarget)
                .filter_by(event_id=event_christmas.id, recipe_id=recipe_cookies.id)
                .first()
            )
            assert db_target is not None
            assert db_target.target_batches == 5

    def test_updates_existing_target(self, test_db, event_christmas, recipe_cookies):
        """Existing target is updated, not duplicated."""
        # Create initial target
        event_service.set_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_cookies.id,
            target_batches=5,
            notes="Initial note",
        )

        # Update it
        result = event_service.set_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_cookies.id,
            target_batches=10,
            notes="Updated note",
        )

        assert result.target_batches == 10
        assert result.notes == "Updated note"

        # Verify only one record exists
        with session_scope() as session:
            count = (
                session.query(EventProductionTarget)
                .filter_by(event_id=event_christmas.id, recipe_id=recipe_cookies.id)
                .count()
            )
            assert count == 1

    def test_validates_positive_target(self, test_db, event_christmas, recipe_cookies):
        """ValueError raised for non-positive target_batches."""
        with pytest.raises(ValueError) as exc_info:
            event_service.set_production_target(
                event_id=event_christmas.id,
                recipe_id=recipe_cookies.id,
                target_batches=0,
            )
        assert "positive" in str(exc_info.value).lower()

        with pytest.raises(ValueError):
            event_service.set_production_target(
                event_id=event_christmas.id,
                recipe_id=recipe_cookies.id,
                target_batches=-5,
            )


class TestGetProductionTargets:
    """Tests for get_production_targets() function."""

    def test_returns_all_targets(
        self, test_db, event_christmas, recipe_cookies, recipe_brownies
    ):
        """Returns all targets for the event."""
        event_service.set_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_cookies.id,
            target_batches=5,
        )
        event_service.set_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_brownies.id,
            target_batches=3,
        )

        result = event_service.get_production_targets(event_christmas.id)

        assert len(result) == 2
        target_batches = {t.target_batches for t in result}
        assert target_batches == {5, 3}

    def test_returns_empty_list(self, test_db, event_christmas):
        """Returns empty list when no targets set."""
        result = event_service.get_production_targets(event_christmas.id)
        assert result == []

    def test_eager_loads_recipe(self, test_db, event_christmas, recipe_cookies):
        """Recipe relationship is eager loaded."""
        event_service.set_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_cookies.id,
            target_batches=5,
        )

        result = event_service.get_production_targets(event_christmas.id)

        assert len(result) == 1
        # Access recipe without triggering additional query (eager loaded)
        assert result[0].recipe is not None
        assert result[0].recipe.name == "Sugar Cookies"


class TestDeleteProductionTarget:
    """Tests for delete_production_target() function."""

    def test_returns_true_when_deleted(self, test_db, event_christmas, recipe_cookies):
        """Returns True when target deleted."""
        event_service.set_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_cookies.id,
            target_batches=5,
        )

        result = event_service.delete_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_cookies.id,
        )

        assert result is True

        # Verify deletion
        with session_scope() as session:
            db_target = (
                session.query(EventProductionTarget)
                .filter_by(event_id=event_christmas.id, recipe_id=recipe_cookies.id)
                .first()
            )
            assert db_target is None

    def test_returns_false_when_not_found(
        self, test_db, event_christmas, recipe_cookies
    ):
        """Returns False when target not found."""
        result = event_service.delete_production_target(
            event_id=event_christmas.id,
            recipe_id=recipe_cookies.id,
        )

        assert result is False


# =============================================================================
# Tests for Assembly Targets
# =============================================================================


class TestSetAssemblyTarget:
    """Tests for set_assembly_target() function."""

    def test_creates_new_target(self, test_db, event_christmas, finished_good_gift_box):
        """New target is created when none exists."""
        result = event_service.set_assembly_target(
            event_id=event_christmas.id,
            finished_good_id=finished_good_gift_box.id,
            target_quantity=20,
            notes="For all relatives",
        )

        assert result.event_id == event_christmas.id
        assert result.finished_good_id == finished_good_gift_box.id
        assert result.target_quantity == 20
        assert result.notes == "For all relatives"

        # Verify in database
        with session_scope() as session:
            db_target = (
                session.query(EventAssemblyTarget)
                .filter_by(
                    event_id=event_christmas.id,
                    finished_good_id=finished_good_gift_box.id,
                )
                .first()
            )
            assert db_target is not None
            assert db_target.target_quantity == 20

    def test_updates_existing_target(
        self, test_db, event_christmas, finished_good_gift_box
    ):
        """Existing target is updated, not duplicated."""
        # Create initial target
        event_service.set_assembly_target(
            event_id=event_christmas.id,
            finished_good_id=finished_good_gift_box.id,
            target_quantity=20,
            notes="Initial note",
        )

        # Update it
        result = event_service.set_assembly_target(
            event_id=event_christmas.id,
            finished_good_id=finished_good_gift_box.id,
            target_quantity=30,
            notes="Updated note",
        )

        assert result.target_quantity == 30
        assert result.notes == "Updated note"

        # Verify only one record exists
        with session_scope() as session:
            count = (
                session.query(EventAssemblyTarget)
                .filter_by(
                    event_id=event_christmas.id,
                    finished_good_id=finished_good_gift_box.id,
                )
                .count()
            )
            assert count == 1

    def test_validates_positive_target(
        self, test_db, event_christmas, finished_good_gift_box
    ):
        """ValueError raised for non-positive target_quantity."""
        with pytest.raises(ValueError) as exc_info:
            event_service.set_assembly_target(
                event_id=event_christmas.id,
                finished_good_id=finished_good_gift_box.id,
                target_quantity=0,
            )
        assert "positive" in str(exc_info.value).lower()

        with pytest.raises(ValueError):
            event_service.set_assembly_target(
                event_id=event_christmas.id,
                finished_good_id=finished_good_gift_box.id,
                target_quantity=-10,
            )


class TestGetAssemblyTargets:
    """Tests for get_assembly_targets() function."""

    def test_returns_all_targets(
        self, test_db, event_christmas, finished_good_gift_box, finished_good_tray
    ):
        """Returns all targets for the event."""
        event_service.set_assembly_target(
            event_id=event_christmas.id,
            finished_good_id=finished_good_gift_box.id,
            target_quantity=20,
        )
        event_service.set_assembly_target(
            event_id=event_christmas.id,
            finished_good_id=finished_good_tray.id,
            target_quantity=10,
        )

        result = event_service.get_assembly_targets(event_christmas.id)

        assert len(result) == 2
        target_quantities = {t.target_quantity for t in result}
        assert target_quantities == {20, 10}

    def test_returns_empty_list(self, test_db, event_christmas):
        """Returns empty list when no targets set."""
        result = event_service.get_assembly_targets(event_christmas.id)
        assert result == []

    def test_eager_loads_finished_good(
        self, test_db, event_christmas, finished_good_gift_box
    ):
        """FinishedGood relationship is eager loaded."""
        event_service.set_assembly_target(
            event_id=event_christmas.id,
            finished_good_id=finished_good_gift_box.id,
            target_quantity=20,
        )

        result = event_service.get_assembly_targets(event_christmas.id)

        assert len(result) == 1
        # Access finished_good without triggering additional query (eager loaded)
        assert result[0].finished_good is not None
        assert result[0].finished_good.display_name == "Cookie Gift Box"


class TestDeleteAssemblyTarget:
    """Tests for delete_assembly_target() function."""

    def test_returns_true_when_deleted(
        self, test_db, event_christmas, finished_good_gift_box
    ):
        """Returns True when target deleted."""
        event_service.set_assembly_target(
            event_id=event_christmas.id,
            finished_good_id=finished_good_gift_box.id,
            target_quantity=20,
        )

        result = event_service.delete_assembly_target(
            event_id=event_christmas.id,
            finished_good_id=finished_good_gift_box.id,
        )

        assert result is True

        # Verify deletion
        with session_scope() as session:
            db_target = (
                session.query(EventAssemblyTarget)
                .filter_by(
                    event_id=event_christmas.id,
                    finished_good_id=finished_good_gift_box.id,
                )
                .first()
            )
            assert db_target is None

    def test_returns_false_when_not_found(
        self, test_db, event_christmas, finished_good_gift_box
    ):
        """Returns False when target not found."""
        result = event_service.delete_assembly_target(
            event_id=event_christmas.id,
            finished_good_id=finished_good_gift_box.id,
        )

        assert result is False
