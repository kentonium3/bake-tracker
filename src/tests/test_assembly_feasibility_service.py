"""Tests for assembly_feasibility_service (F076).

Feature 076: Assembly Feasibility & Single-Screen Planning
Work Package: WP02 - Service Unit Tests

This test module verifies:
1. Basic feasibility calculation (T006)
2. Shortfall detection (T007)
3. Bundle component validation (T008)
4. Edge cases: empty event, missing decisions (T009)
5. Decision coverage metrics (T010)
"""

import pytest
from datetime import date

from src.models import Event, Recipe, FinishedUnit, FinishedGood, BatchDecision
from src.models.event_finished_good import EventFinishedGood
from src.models.composition import Composition
from src.models.finished_unit import YieldMode
from src.services.assembly_feasibility_service import (
    calculate_assembly_feasibility,
    AssemblyFeasibilityResult,
    FGFeasibilityStatus,
    ComponentStatus,
)
from src.services.exceptions import ValidationError


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def test_event(test_db):
    """Create a test event."""
    session = test_db()
    event = Event(name="Test Event", event_date=date(2026, 1, 1), year=2026)
    session.add(event)
    session.commit()
    return event.id


@pytest.fixture(scope="function")
def basic_recipe(test_db):
    """Create a basic recipe."""
    session = test_db()
    recipe = Recipe(name="Test Cookie Recipe", category="Cookies")
    session.add(recipe)
    session.commit()
    return recipe.id


@pytest.fixture(scope="function")
def basic_finished_unit(test_db, basic_recipe):
    """Create a finished unit that yields 10 items per batch."""
    session = test_db()
    fu = FinishedUnit(
        display_name="Test Cookies",
        slug="test-cookies",
        recipe_id=basic_recipe,
        items_per_batch=10,
        yield_mode=YieldMode.DISCRETE_COUNT,
        item_unit="cookies",
    )
    session.add(fu)
    session.commit()
    return fu.id


@pytest.fixture(scope="function")
def basic_finished_good(test_db, basic_finished_unit):
    """Create a finished good with one FU component (1 cookie per box)."""
    session = test_db()
    fg = FinishedGood(
        slug="cookie-box",
        display_name="Cookie Box",
    )
    session.add(fg)
    session.flush()

    # Add FU component via Composition
    comp = Composition(
        assembly_id=fg.id,
        finished_unit_id=basic_finished_unit,
        component_quantity=1,
    )
    session.add(comp)
    session.commit()
    return fg.id


@pytest.fixture(scope="function")
def second_recipe(test_db):
    """Create a second recipe for brownies."""
    session = test_db()
    recipe = Recipe(name="Brownie Recipe", category="Brownies")
    session.add(recipe)
    session.commit()
    return recipe.id


@pytest.fixture(scope="function")
def second_finished_unit(test_db, second_recipe):
    """Create a second FU (brownies) with 8 items per batch."""
    session = test_db()
    fu = FinishedUnit(
        display_name="Test Brownies",
        slug="test-brownies",
        recipe_id=second_recipe,
        items_per_batch=8,
        yield_mode=YieldMode.DISCRETE_COUNT,
        item_unit="brownies",
    )
    session.add(fu)
    session.commit()
    return fu.id


@pytest.fixture(scope="function")
def bundle_finished_good(test_db, basic_finished_unit, second_finished_unit):
    """Create a bundle FG with two FU components (2 cookies + 2 brownies per box)."""
    session = test_db()
    fg = FinishedGood(
        slug="assorted-box",
        display_name="Assorted Box",
    )
    session.add(fg)
    session.flush()

    # Add both FU components via Composition
    comp1 = Composition(
        assembly_id=fg.id,
        finished_unit_id=basic_finished_unit,
        component_quantity=2,  # 2 cookies per box
    )
    comp2 = Composition(
        assembly_id=fg.id,
        finished_unit_id=second_finished_unit,
        component_quantity=2,  # 2 brownies per box
    )
    session.add(comp1)
    session.add(comp2)
    session.commit()
    return fg.id


# =============================================================================
# T006: Test Basic Feasibility (Sufficient Production)
# =============================================================================


class TestBasicFeasibility:
    """Tests for T006 - Basic feasibility with sufficient production."""

    def test_basic_feasibility_sufficient(
        self, test_db, test_event, basic_finished_good, basic_finished_unit, basic_recipe
    ):
        """Test that sufficient production yields can_assemble=True."""
        session = test_db()

        # Add FG to event (need 5 cookie boxes = 5 cookies, since 1 cookie per box)
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=basic_finished_good,
            quantity=5,
        )
        session.add(efg)

        # Add batch decision: 1 batch = 10 cookies (more than 5 needed)
        bd = BatchDecision(
            event_id=test_event,
            finished_unit_id=basic_finished_unit,
            recipe_id=basic_recipe,
            batches=1,
        )
        session.add(bd)
        session.commit()

        # Calculate feasibility
        result = calculate_assembly_feasibility(test_event)

        assert result.overall_feasible is True
        assert len(result.finished_goods) == 1
        assert result.finished_goods[0].can_assemble is True
        assert result.finished_goods[0].shortfall == 0
        assert result.finished_goods[0].quantity_needed == 5

    def test_basic_feasibility_exact_match(
        self, test_db, test_event, basic_finished_good, basic_finished_unit, basic_recipe
    ):
        """Test that exact production match yields can_assemble=True."""
        session = test_db()

        # Add FG to event (need 10 cookie boxes = 10 cookies)
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=basic_finished_good,
            quantity=10,
        )
        session.add(efg)

        # Add batch decision: 1 batch = 10 cookies (exactly 10 needed)
        bd = BatchDecision(
            event_id=test_event,
            finished_unit_id=basic_finished_unit,
            recipe_id=basic_recipe,
            batches=1,
        )
        session.add(bd)
        session.commit()

        result = calculate_assembly_feasibility(test_event)

        assert result.overall_feasible is True
        assert result.finished_goods[0].can_assemble is True
        assert result.finished_goods[0].shortfall == 0


# =============================================================================
# T007: Test Shortfall Detection
# =============================================================================


class TestShortfallDetection:
    """Tests for T007 - Shortfall detection when production < needed."""

    def test_shortfall_detection(
        self, test_db, test_event, basic_finished_good, basic_finished_unit, basic_recipe
    ):
        """Test that insufficient production yields can_assemble=False with shortfall."""
        session = test_db()

        # Add FG to event (need 15 cookie boxes = 15 cookies)
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=basic_finished_good,
            quantity=15,
        )
        session.add(efg)

        # Add batch decision: 1 batch = 10 cookies (less than 15 needed)
        bd = BatchDecision(
            event_id=test_event,
            finished_unit_id=basic_finished_unit,
            recipe_id=basic_recipe,
            batches=1,
        )
        session.add(bd)
        session.commit()

        result = calculate_assembly_feasibility(test_event)

        assert result.overall_feasible is False
        assert len(result.finished_goods) == 1
        fg_status = result.finished_goods[0]
        assert fg_status.can_assemble is False
        assert fg_status.shortfall > 0  # Should be 5 (15 needed - 10 available)
        assert fg_status.quantity_needed == 15

    def test_shortfall_amount_calculation(
        self, test_db, test_event, basic_finished_good, basic_finished_unit, basic_recipe
    ):
        """Test that shortfall amount is calculated correctly."""
        session = test_db()

        # Add FG to event (need 25 cookie boxes = 25 cookies)
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=basic_finished_good,
            quantity=25,
        )
        session.add(efg)

        # Add batch decision: 2 batches = 20 cookies (5 short)
        bd = BatchDecision(
            event_id=test_event,
            finished_unit_id=basic_finished_unit,
            recipe_id=basic_recipe,
            batches=2,
        )
        session.add(bd)
        session.commit()

        result = calculate_assembly_feasibility(test_event)

        fg_status = result.finished_goods[0]
        # 20 available / 25 needed = 0.8 ratio
        # achievable = int(25 * 0.8) = 20
        # shortfall = 25 - 20 = 5
        assert fg_status.shortfall == 5
        assert fg_status.can_assemble is False


# =============================================================================
# T008: Test Bundle Component Validation
# =============================================================================


class TestBundleValidation:
    """Tests for T008 - Bundle component validation with multiple FUs."""

    def test_bundle_validation_all_sufficient(
        self,
        test_db,
        test_event,
        bundle_finished_good,
        basic_finished_unit,
        second_finished_unit,
        basic_recipe,
        second_recipe,
    ):
        """Test bundle where all components are sufficient."""
        session = test_db()

        # Need 3 assorted boxes = 6 cookies + 6 brownies (2 each per box)
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=bundle_finished_good,
            quantity=3,
        )
        session.add(efg)

        # 1 batch cookies = 10 (need 6)
        bd1 = BatchDecision(
            event_id=test_event,
            finished_unit_id=basic_finished_unit,
            recipe_id=basic_recipe,
            batches=1,
        )
        session.add(bd1)

        # 1 batch brownies = 8 (need 6)
        bd2 = BatchDecision(
            event_id=test_event,
            finished_unit_id=second_finished_unit,
            recipe_id=second_recipe,
            batches=1,
        )
        session.add(bd2)
        session.commit()

        result = calculate_assembly_feasibility(test_event)

        assert result.overall_feasible is True
        fg_status = result.finished_goods[0]
        assert fg_status.can_assemble is True
        assert len(fg_status.components) == 2

        # Verify all components are sufficient
        for comp in fg_status.components:
            assert comp.is_sufficient is True

    def test_bundle_one_component_short(
        self,
        test_db,
        test_event,
        bundle_finished_good,
        basic_finished_unit,
        second_finished_unit,
        basic_recipe,
        second_recipe,
    ):
        """Test bundle where one component is insufficient."""
        session = test_db()

        # Need 5 assorted boxes = 10 cookies + 10 brownies (2 each per box)
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=bundle_finished_good,
            quantity=5,
        )
        session.add(efg)

        # 1 batch cookies = 10 (need 10) - SUFFICIENT
        bd1 = BatchDecision(
            event_id=test_event,
            finished_unit_id=basic_finished_unit,
            recipe_id=basic_recipe,
            batches=1,
        )
        session.add(bd1)

        # 1 batch brownies = 8 (need 10) - INSUFFICIENT
        bd2 = BatchDecision(
            event_id=test_event,
            finished_unit_id=second_finished_unit,
            recipe_id=second_recipe,
            batches=1,
        )
        session.add(bd2)
        session.commit()

        result = calculate_assembly_feasibility(test_event)

        assert result.overall_feasible is False
        fg_status = result.finished_goods[0]
        assert fg_status.can_assemble is False

        # One component is insufficient
        insufficient = [c for c in fg_status.components if not c.is_sufficient]
        assert len(insufficient) == 1
        assert insufficient[0].finished_unit_name == "Test Brownies"

    def test_bundle_both_components_short(
        self,
        test_db,
        test_event,
        bundle_finished_good,
        basic_finished_unit,
        second_finished_unit,
        basic_recipe,
        second_recipe,
    ):
        """Test bundle where both components are insufficient."""
        session = test_db()

        # Need 10 assorted boxes = 20 cookies + 20 brownies
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=bundle_finished_good,
            quantity=10,
        )
        session.add(efg)

        # 1 batch cookies = 10 (need 20) - SHORT
        bd1 = BatchDecision(
            event_id=test_event,
            finished_unit_id=basic_finished_unit,
            recipe_id=basic_recipe,
            batches=1,
        )
        session.add(bd1)

        # 1 batch brownies = 8 (need 20) - SHORT
        bd2 = BatchDecision(
            event_id=test_event,
            finished_unit_id=second_finished_unit,
            recipe_id=second_recipe,
            batches=1,
        )
        session.add(bd2)
        session.commit()

        result = calculate_assembly_feasibility(test_event)

        assert result.overall_feasible is False
        fg_status = result.finished_goods[0]
        assert fg_status.can_assemble is False

        # Both components are insufficient
        insufficient = [c for c in fg_status.components if not c.is_sufficient]
        assert len(insufficient) == 2


# =============================================================================
# T009: Test Empty Event and Missing Batch Decisions
# =============================================================================


class TestEdgeCases:
    """Tests for T009 - Edge cases: empty event, missing decisions."""

    def test_empty_event_no_fgs(self, test_db, test_event):
        """Test event with no FG selections returns feasible."""
        result = calculate_assembly_feasibility(test_event)

        assert result.overall_feasible is True
        assert len(result.finished_goods) == 0
        assert result.decided_count == 0
        assert result.total_fu_count == 0

    def test_no_batch_decisions(self, test_db, test_event, basic_finished_good):
        """Test event with FGs but no batch decisions."""
        session = test_db()

        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=basic_finished_good,
            quantity=5,
        )
        session.add(efg)
        session.commit()

        result = calculate_assembly_feasibility(test_event)

        # Can't assemble without decisions - FU has 0 available
        assert result.overall_feasible is False
        assert result.decided_count == 0
        assert result.total_fu_count > 0

        # FG should show as not assemblable
        fg_status = result.finished_goods[0]
        assert fg_status.can_assemble is False

    def test_event_not_found(self, test_db):
        """Test that non-existent event raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            calculate_assembly_feasibility(99999)

        assert "Event 99999 not found" in str(exc_info.value)

    def test_zero_quantity_fg(self, test_db, test_event, basic_finished_good):
        """Test FG with zero quantity is handled gracefully.

        Note: EventFinishedGood has a CHECK constraint requiring quantity > 0,
        so this would fail at the database level. This test documents the
        expected behavior if such data somehow existed.
        """
        # This would fail with ck_event_fg_quantity_positive constraint
        # We test the service handles it gracefully if it received such data
        pass  # Skip - constraint prevents this scenario


# =============================================================================
# T010: Test Decision Coverage Metrics
# =============================================================================


class TestDecisionCoverage:
    """Tests for T010 - Decision coverage metrics (decided_count vs total_fu_count)."""

    def test_decision_coverage_full(
        self, test_db, test_event, basic_finished_good, basic_finished_unit, basic_recipe
    ):
        """Test that full decision coverage is tracked correctly."""
        session = test_db()

        # Add FG that needs 1 FU
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=basic_finished_good,
            quantity=5,
        )
        session.add(efg)

        # Add decision for that FU
        bd = BatchDecision(
            event_id=test_event,
            finished_unit_id=basic_finished_unit,
            recipe_id=basic_recipe,
            batches=1,
        )
        session.add(bd)
        session.commit()

        result = calculate_assembly_feasibility(test_event)

        # 1 FU required, 1 decision made
        assert result.total_fu_count == 1
        assert result.decided_count == 1

    def test_decision_coverage_partial(
        self,
        test_db,
        test_event,
        bundle_finished_good,
        basic_finished_unit,
        second_finished_unit,
        basic_recipe,
    ):
        """Test that partial decision coverage is tracked correctly."""
        session = test_db()

        # Add bundle that needs 2 FUs
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=bundle_finished_good,
            quantity=1,
        )
        session.add(efg)

        # Only add decision for one FU (cookies only)
        bd1 = BatchDecision(
            event_id=test_event,
            finished_unit_id=basic_finished_unit,
            recipe_id=basic_recipe,
            batches=1,
        )
        session.add(bd1)
        session.commit()

        result = calculate_assembly_feasibility(test_event)

        # 2 FUs needed, but only 1 decision made
        assert result.total_fu_count == 2
        assert result.decided_count == 1

    def test_decision_coverage_none(
        self, test_db, test_event, bundle_finished_good
    ):
        """Test that zero decision coverage is tracked correctly."""
        session = test_db()

        # Add bundle that needs 2 FUs, but no decisions
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=bundle_finished_good,
            quantity=1,
        )
        session.add(efg)
        session.commit()

        result = calculate_assembly_feasibility(test_event)

        # 2 FUs needed, 0 decisions made
        assert result.total_fu_count == 2
        assert result.decided_count == 0

    def test_multiple_fgs_coverage(
        self,
        test_db,
        test_event,
        basic_finished_good,
        bundle_finished_good,
        basic_finished_unit,
        second_finished_unit,
        basic_recipe,
        second_recipe,
    ):
        """Test coverage with multiple FGs sharing FUs."""
        session = test_db()

        # Add basic FG (needs cookies)
        efg1 = EventFinishedGood(
            event_id=test_event,
            finished_good_id=basic_finished_good,
            quantity=2,
        )
        session.add(efg1)

        # Add bundle FG (needs cookies AND brownies)
        efg2 = EventFinishedGood(
            event_id=test_event,
            finished_good_id=bundle_finished_good,
            quantity=1,
        )
        session.add(efg2)

        # Add decisions for both FUs
        bd1 = BatchDecision(
            event_id=test_event,
            finished_unit_id=basic_finished_unit,
            recipe_id=basic_recipe,
            batches=1,
        )
        bd2 = BatchDecision(
            event_id=test_event,
            finished_unit_id=second_finished_unit,
            recipe_id=second_recipe,
            batches=1,
        )
        session.add(bd1)
        session.add(bd2)
        session.commit()

        result = calculate_assembly_feasibility(test_event)

        # total_fu_count = total FU requirements (including duplicates)
        # basic_finished_good needs: 2 cookies (1 FU requirement)
        # bundle_finished_good needs: 2 cookies + 2 brownies (2 FU requirements)
        # Total FU requirements: 3
        assert result.total_fu_count == 3
        # decided_count = unique FUs that have batch decisions
        # Both cookies and brownies have decisions
        assert result.decided_count == 2


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for assembly_feasibility_service."""

    def test_component_status_details(
        self, test_db, test_event, bundle_finished_good, basic_finished_unit,
        second_finished_unit, basic_recipe, second_recipe
    ):
        """Test that component status includes correct details."""
        session = test_db()

        # Need 2 assorted boxes = 4 cookies + 4 brownies
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=bundle_finished_good,
            quantity=2,
        )
        session.add(efg)

        # 1 batch cookies = 10 (need 4)
        bd1 = BatchDecision(
            event_id=test_event,
            finished_unit_id=basic_finished_unit,
            recipe_id=basic_recipe,
            batches=1,
        )
        # No brownies decision - will be 0 available
        session.add(bd1)
        session.commit()

        result = calculate_assembly_feasibility(test_event)

        fg_status = result.finished_goods[0]
        assert len(fg_status.components) == 2

        # Find cookie component
        cookie_comp = next(
            c for c in fg_status.components if c.finished_unit_name == "Test Cookies"
        )
        assert cookie_comp.quantity_needed == 4  # 2 boxes * 2 per box
        assert cookie_comp.quantity_available == 10  # 1 batch * 10
        assert cookie_comp.is_sufficient is True

        # Find brownie component
        brownie_comp = next(
            c for c in fg_status.components if c.finished_unit_name == "Test Brownies"
        )
        assert brownie_comp.quantity_needed == 4
        assert brownie_comp.quantity_available == 0  # No decision
        assert brownie_comp.is_sufficient is False

    def test_session_parameter_works(
        self, test_db, test_event, basic_finished_good, basic_finished_unit, basic_recipe
    ):
        """Test that passing session parameter works correctly."""
        from src.services.database import session_scope

        session = test_db()

        # Setup data
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=basic_finished_good,
            quantity=5,
        )
        session.add(efg)

        bd = BatchDecision(
            event_id=test_event,
            finished_unit_id=basic_finished_unit,
            recipe_id=basic_recipe,
            batches=1,
        )
        session.add(bd)
        session.commit()

        # Test with explicit session
        with session_scope() as sess:
            result = calculate_assembly_feasibility(test_event, session=sess)
            assert result.overall_feasible is True
            assert len(result.finished_goods) == 1
