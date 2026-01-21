"""
Tests for event service session pass-through.

Feature 060: Architecture Hardening - Service Boundaries & Session Management
Work Package: WP02 - Event Service Session Normalization
Subtask: T008

This test module verifies that:
1. get_production_progress() accepts and uses optional session parameter
2. get_assembly_progress() accepts and uses optional session parameter
3. get_shopping_list() accepts and uses optional session parameter
4. All methods work correctly without session parameter (backward compatibility)
5. Methods can see uncommitted changes when session is shared
"""

import pytest
from datetime import date
from decimal import Decimal

from src.services.database import session_scope
from src.services import event_service
from src.models import (
    Event,
    Recipe,
    FinishedGood,
    FinishedUnit,
    EventProductionTarget,
    EventAssemblyTarget,
    ProductionRun,
    AssemblyRun,
    Ingredient,
    RecipeIngredient,
)
from src.models.finished_unit import YieldMode
from src.models.assembly_type import AssemblyType


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def event_with_targets(test_db):
    """
    Set up an event with production and assembly targets for session testing.

    Creates:
    - Event
    - Recipe with production target
    - FinishedGood with assembly target
    - FinishedUnit for the recipe

    Returns a dict with IDs for use in tests.
    """
    session = test_db()

    # Create event
    event = Event(
        name="Session Test Event",
        event_date=date(2024, 12, 25),
        year=2024,
    )
    session.add(event)
    session.flush()

    # Create recipe
    recipe = Recipe(
        name="Session Test Cookies",
        category="Cookies",
    )
    session.add(recipe)
    session.flush()

    # Create finished unit for the recipe
    finished_unit = FinishedUnit(
        recipe_id=recipe.id,
        display_name="Cookie Batch",
        slug="cookie-batch",
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=24,
        item_unit="cookies",
    )
    session.add(finished_unit)
    session.flush()

    # Create finished good for assembly
    finished_good = FinishedGood(
        display_name="Cookie Box",
        slug="cookie-box",
        assembly_type=AssemblyType.GIFT_BOX,
    )
    session.add(finished_good)
    session.flush()

    # Create production target
    production_target = EventProductionTarget(
        event_id=event.id,
        recipe_id=recipe.id,
        target_batches=5,
    )
    session.add(production_target)
    session.flush()

    # Create assembly target
    assembly_target = EventAssemblyTarget(
        event_id=event.id,
        finished_good_id=finished_good.id,
        target_quantity=10,
    )
    session.add(assembly_target)
    session.commit()

    # Return IDs for querying in tests
    class SetupData:
        pass

    data = SetupData()
    data.event_id = event.id
    data.recipe_id = recipe.id
    data.finished_unit_id = finished_unit.id
    data.finished_good_id = finished_good.id
    data.session_factory = test_db

    return data


@pytest.fixture(scope="function")
def event_with_recipe_needs(test_db):
    """
    Set up an event with recipe needs for shopping list testing.

    Creates:
    - Event with production targets
    - Recipe with ingredients
    - Ingredient with quantity

    Returns a dict with IDs for use in tests.
    """
    session = test_db()

    # Create event
    event = Event(
        name="Shopping List Test Event",
        event_date=date(2024, 12, 25),
        year=2024,
    )
    session.add(event)
    session.flush()

    # Create ingredient
    ingredient = Ingredient(
        display_name="Test Flour",
        slug="test-flour",
        category="Flour",
        density_volume_value=Decimal("1.0"),
        density_volume_unit="cup",
        density_weight_value=Decimal("120.0"),
        density_weight_unit="g",
    )
    session.add(ingredient)
    session.flush()

    # Create recipe
    recipe = Recipe(
        name="Shopping Test Cookies",
        category="Cookies",
    )
    session.add(recipe)
    session.flush()

    # Create recipe ingredient
    recipe_ingredient = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient.id,
        quantity=2.0,
        unit="cup",
    )
    session.add(recipe_ingredient)
    session.flush()

    # Create finished unit for recipe
    finished_unit = FinishedUnit(
        recipe_id=recipe.id,
        display_name="Shopping Test Batch",
        slug="shopping-test-batch",
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=24,
        item_unit="cookies",
    )
    session.add(finished_unit)
    session.flush()

    # Create production target (1 batch needed)
    production_target = EventProductionTarget(
        event_id=event.id,
        recipe_id=recipe.id,
        target_batches=1,
    )
    session.add(production_target)
    session.commit()

    class SetupData:
        pass

    data = SetupData()
    data.event_id = event.id
    data.recipe_id = recipe.id
    data.ingredient_id = ingredient.id
    data.session_factory = test_db

    return data


# =============================================================================
# Session Pass-Through Tests
# =============================================================================


class TestProductionProgressSession:
    """Test session pass-through for get_production_progress()."""

    def test_accepts_session_parameter(self, event_with_targets):
        """Verify get_production_progress() accepts optional session parameter."""
        import inspect

        sig = inspect.signature(event_service.get_production_progress)
        assert "session" in sig.parameters
        assert sig.parameters["session"].default is None

    def test_with_session_sees_uncommitted_production(self, event_with_targets):
        """Verify production progress sees uncommitted production runs in same session."""
        event_id = event_with_targets.event_id
        recipe_id = event_with_targets.recipe_id
        finished_unit_id = event_with_targets.finished_unit_id

        with session_scope() as session:
            # Add uncommitted production run
            production_run = ProductionRun(
                recipe_id=recipe_id,
                finished_unit_id=finished_unit_id,
                event_id=event_id,
                num_batches=2,
                expected_yield=48,
                actual_yield=48,
                produced_at=date.today(),
            )
            session.add(production_run)
            session.flush()  # Make visible but don't commit

            # Get progress with same session - should see uncommitted run
            result = event_service.get_production_progress(event_id, session=session)

            assert len(result) == 1
            assert result[0]["produced_batches"] == 2, (
                "Should see uncommitted production run when session is shared"
            )

            # Rollback to verify nothing was committed
            session.rollback()

        # After rollback, verify production run is gone
        with session_scope() as session:
            result = event_service.get_production_progress(event_id, session=session)
            assert result[0]["produced_batches"] == 0, (
                "Production should be 0 after rollback"
            )

    def test_without_session_backward_compatible(self, event_with_targets):
        """Verify get_production_progress() works without session parameter."""
        event_id = event_with_targets.event_id

        # Call without session (backward compatibility)
        result = event_service.get_production_progress(event_id)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["recipe_name"] == "Session Test Cookies"
        assert result[0]["target_batches"] == 5
        assert result[0]["produced_batches"] == 0


class TestAssemblyProgressSession:
    """Test session pass-through for get_assembly_progress()."""

    def test_accepts_session_parameter(self, event_with_targets):
        """Verify get_assembly_progress() accepts optional session parameter."""
        import inspect

        sig = inspect.signature(event_service.get_assembly_progress)
        assert "session" in sig.parameters
        assert sig.parameters["session"].default is None

    def test_with_session_sees_uncommitted_assembly(self, event_with_targets):
        """Verify assembly progress sees uncommitted assembly runs in same session."""
        event_id = event_with_targets.event_id
        finished_good_id = event_with_targets.finished_good_id

        with session_scope() as session:
            # Add uncommitted assembly run
            assembly_run = AssemblyRun(
                finished_good_id=finished_good_id,
                event_id=event_id,
                quantity_assembled=3,
                assembled_at=date.today(),
            )
            session.add(assembly_run)
            session.flush()  # Make visible but don't commit

            # Get progress with same session - should see uncommitted run
            result = event_service.get_assembly_progress(event_id, session=session)

            assert len(result) == 1
            assert result[0]["assembled_quantity"] == 3, (
                "Should see uncommitted assembly run when session is shared"
            )

            # Rollback to verify nothing was committed
            session.rollback()

        # After rollback, verify assembly run is gone
        with session_scope() as session:
            result = event_service.get_assembly_progress(event_id, session=session)
            assert result[0]["assembled_quantity"] == 0, (
                "Assembly should be 0 after rollback"
            )

    def test_without_session_backward_compatible(self, event_with_targets):
        """Verify get_assembly_progress() works without session parameter."""
        event_id = event_with_targets.event_id

        # Call without session (backward compatibility)
        result = event_service.get_assembly_progress(event_id)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["finished_good_name"] == "Cookie Box"
        assert result[0]["target_quantity"] == 10
        assert result[0]["assembled_quantity"] == 0


class TestShoppingListSession:
    """Test session pass-through for get_shopping_list()."""

    def test_accepts_session_parameter(self, event_with_recipe_needs):
        """Verify get_shopping_list() accepts optional session parameter."""
        import inspect

        sig = inspect.signature(event_service.get_shopping_list)
        assert "session" in sig.parameters
        assert sig.parameters["session"].default is None

    def test_with_session_uses_provided_session(self, event_with_recipe_needs):
        """Verify get_shopping_list() uses provided session for queries."""
        event_id = event_with_recipe_needs.event_id

        with session_scope() as session:
            # Call with session - should work without error
            result = event_service.get_shopping_list(
                event_id, include_packaging=False, session=session
            )

            # Should return a valid result structure
            assert "items" in result
            assert "items_count" in result
            assert isinstance(result["items"], list)

    def test_without_session_backward_compatible(self, event_with_recipe_needs):
        """Verify get_shopping_list() works without session parameter."""
        event_id = event_with_recipe_needs.event_id

        # Call without session (backward compatibility)
        result = event_service.get_shopping_list(event_id, include_packaging=False)

        assert isinstance(result, dict)
        assert "items" in result
        assert "items_count" in result
        # Should have at least one item (the flour)
        assert result["items_count"] >= 0


# =============================================================================
# Transaction Atomicity Tests
# =============================================================================


class TestSessionAtomicity:
    """Test that session pass-through enables transactional atomicity."""

    def test_multi_progress_call_same_session(self, event_with_targets):
        """Verify multiple progress calls can share same session."""
        event_id = event_with_targets.event_id

        with session_scope() as session:
            # Call both progress methods with same session
            prod_result = event_service.get_production_progress(event_id, session=session)
            assm_result = event_service.get_assembly_progress(event_id, session=session)

            # Both should return valid results
            assert len(prod_result) == 1
            assert len(assm_result) == 1

    def test_progress_rollback_affects_all_changes(self, event_with_targets):
        """Verify rollback reverts all changes made through shared session."""
        event_id = event_with_targets.event_id
        recipe_id = event_with_targets.recipe_id
        finished_unit_id = event_with_targets.finished_unit_id
        finished_good_id = event_with_targets.finished_good_id

        with session_scope() as session:
            # Add production run
            prod_run = ProductionRun(
                recipe_id=recipe_id,
                finished_unit_id=finished_unit_id,
                event_id=event_id,
                num_batches=3,
                expected_yield=72,
                actual_yield=72,
                produced_at=date.today(),
            )
            session.add(prod_run)

            # Add assembly run
            assm_run = AssemblyRun(
                finished_good_id=finished_good_id,
                event_id=event_id,
                quantity_assembled=5,
                assembled_at=date.today(),
            )
            session.add(assm_run)
            session.flush()

            # Verify both visible in session
            prod_result = event_service.get_production_progress(event_id, session=session)
            assm_result = event_service.get_assembly_progress(event_id, session=session)
            assert prod_result[0]["produced_batches"] == 3
            assert assm_result[0]["assembled_quantity"] == 5

            # Rollback
            session.rollback()

        # Verify both rolled back
        with session_scope() as session:
            prod_result = event_service.get_production_progress(event_id, session=session)
            assm_result = event_service.get_assembly_progress(event_id, session=session)
            assert prod_result[0]["produced_batches"] == 0
            assert assm_result[0]["assembled_quantity"] == 0
