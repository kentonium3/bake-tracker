"""
Integration tests for F066 Service Decoupling.

Verifies that planning_service and batch_calculation use the
get_finished_units() primitive instead of accessing recipe.finished_units directly.

This is important for:
1. Variant recipes: Primitives handle yield inheritance correctly
2. Maintainability: Single point of access for yield data
3. Testing: Easier to mock and verify behavior

Reference: kitty-specs/066-recipe-variant-yield-remediation/spec.md
"""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

from src.models import (
    Event,
    EventProductionTarget,
    Recipe,
    FinishedUnit,
)
from src.models.event import OutputMode


class TestPlanningServiceDecoupling:
    """T016: Verify planning_service uses get_finished_units() primitive."""

    @pytest.fixture
    def bulk_count_event_setup(self, test_db):
        """Create event with BULK_COUNT output mode and production targets."""
        session = test_db()

        # Create recipe
        recipe = Recipe(
            name="Test Cookies",
            category="Cookies",
        )
        session.add(recipe)
        session.flush()

        # Create finished unit for the recipe
        finished_unit = FinishedUnit(
            recipe_id=recipe.id,
            slug="chocolate-chip-cookie",
            display_name="Chocolate Chip Cookie",
            item_unit="cookie",
            items_per_batch=24,
            yield_mode="discrete_count",
        )
        session.add(finished_unit)
        session.flush()

        # Create event with BULK_COUNT output mode
        event = Event(
            name="Test Event",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BULK_COUNT,
        )
        session.add(event)
        session.flush()

        # Create production target
        target = EventProductionTarget(
            event_id=event.id,
            recipe_id=recipe.id,
            target_batches=5,
        )
        session.add(target)
        session.commit()

        return {
            "session": session,
            "event": event,
            "recipe": recipe,
            "finished_unit": finished_unit,
            "target": target,
        }

    @patch("src.services.planning.planning_service.recipe_service.get_finished_units")
    def test_calculate_bulk_requirements_uses_primitive(
        self, mock_get_fus, bulk_count_event_setup
    ):
        """
        Planning service's _calculate_bulk_requirements should call
        get_finished_units() instead of accessing recipe.finished_units directly.
        """
        from src.services.planning.planning_service import _calculate_bulk_requirements

        setup = bulk_count_event_setup
        session = setup["session"]
        event = setup["event"]
        recipe = setup["recipe"]

        # Configure mock to return yield data
        mock_get_fus.return_value = [
            {
                "id": 1,
                "slug": "test-cookie",
                "display_name": "Test Cookie",
                "items_per_batch": 24,
                "item_unit": "cookie",
                "yield_mode": "discrete_count",
            }
        ]

        # Call the function that should use the primitive
        results = _calculate_bulk_requirements(event, session)

        # Verify the primitive was called
        mock_get_fus.assert_called()

        # Verify it was called with the recipe_id
        call_args_list = mock_get_fus.call_args_list
        assert len(call_args_list) > 0
        # Check that recipe_id was passed
        first_call = call_args_list[0]
        assert first_call[0][0] == recipe.id  # First positional arg is recipe_id

    @patch("src.services.planning.planning_service.recipe_service.get_finished_units")
    def test_bulk_requirements_returns_correct_units(
        self, mock_get_fus, bulk_count_event_setup
    ):
        """
        Verify that _calculate_bulk_requirements uses the items_per_batch
        from the primitive return value, not from direct model access.
        """
        from src.services.planning.planning_service import _calculate_bulk_requirements

        setup = bulk_count_event_setup
        session = setup["session"]
        event = setup["event"]

        # Configure mock with specific items_per_batch
        mock_items_per_batch = 48  # Different from actual DB value
        mock_get_fus.return_value = [
            {
                "id": 99,
                "slug": "mock-cookie",
                "display_name": "Mock Cookie",
                "items_per_batch": mock_items_per_batch,
                "item_unit": "cookie",
                "yield_mode": "discrete_count",
            }
        ]

        # Call the function
        results = _calculate_bulk_requirements(event, session)

        # Verify result uses mocked items_per_batch
        # Target batches is 5, items_per_batch from mock is 48
        # units_needed = target_batches * items_per_batch = 5 * 48 = 240
        assert len(results) == 1
        assert results[0].units_needed == 5 * mock_items_per_batch
        assert results[0].yield_per_batch == mock_items_per_batch


class TestBatchCalculationDecoupling:
    """T017: Verify batch_calculation uses get_finished_units() primitive."""

    @pytest.fixture
    def recipe_with_finished_units(self, test_db):
        """Create recipe with finished units for batch calculation testing."""
        session = test_db()

        # Create recipe
        recipe = Recipe(
            name="Test Brownies",
            category="Brownies",
        )
        session.add(recipe)
        session.flush()

        # Create finished unit for the recipe
        finished_unit = FinishedUnit(
            recipe_id=recipe.id,
            slug="fudge-brownie",
            display_name="Fudge Brownie",
            item_unit="brownie",
            items_per_batch=12,
            yield_mode="discrete_count",
        )
        session.add(finished_unit)
        session.commit()

        return {
            "session": session,
            "recipe": recipe,
            "finished_unit": finished_unit,
        }

    @patch("src.services.planning.batch_calculation.recipe_service.get_finished_units")
    def test_aggregate_by_recipe_uses_primitive(
        self, mock_get_fus, recipe_with_finished_units
    ):
        """
        Batch calculation's aggregate_by_recipe should call
        get_finished_units() instead of accessing recipe.finished_units directly.
        """
        from src.services.planning.batch_calculation import aggregate_by_recipe

        setup = recipe_with_finished_units
        session = setup["session"]
        recipe = setup["recipe"]
        finished_unit = setup["finished_unit"]

        # Configure mock to return yield data
        mock_get_fus.return_value = [
            {
                "id": finished_unit.id,
                "slug": "fudge-brownie",
                "display_name": "Fudge Brownie",
                "items_per_batch": 12,
                "item_unit": "brownie",
                "yield_mode": "discrete_count",
            }
        ]

        # Create unit_quantities dict (FinishedUnit ID -> quantity needed)
        unit_quantities = {finished_unit.id: 36}  # Need 36 brownies

        # Call the function that should use the primitive
        results = aggregate_by_recipe(unit_quantities, session=session)

        # Verify the primitive was called
        mock_get_fus.assert_called()

        # Verify it was called with the recipe_id
        call_args_list = mock_get_fus.call_args_list
        assert len(call_args_list) > 0
        first_call = call_args_list[0]
        assert first_call[0][0] == recipe.id  # First positional arg is recipe_id

    @patch("src.services.planning.batch_calculation.recipe_service.get_finished_units")
    def test_aggregate_by_recipe_uses_mocked_yield(
        self, mock_get_fus, recipe_with_finished_units
    ):
        """
        Verify that aggregate_by_recipe uses the items_per_batch
        from the primitive return value, not from direct model access.
        """
        from src.services.planning.batch_calculation import aggregate_by_recipe

        setup = recipe_with_finished_units
        session = setup["session"]
        finished_unit = setup["finished_unit"]

        # Configure mock with specific items_per_batch (different from DB)
        mock_items_per_batch = 24  # Double the actual DB value (12)
        mock_get_fus.return_value = [
            {
                "id": finished_unit.id,
                "slug": "mock-brownie",
                "display_name": "Mock Brownie",
                "items_per_batch": mock_items_per_batch,
                "item_unit": "brownie",
                "yield_mode": "discrete_count",
            }
        ]

        # Create unit_quantities dict
        unit_quantities = {finished_unit.id: 48}  # Need 48 brownies

        # Call the function
        results = aggregate_by_recipe(unit_quantities, session=session)

        # Verify result uses mocked items_per_batch
        assert len(results) == 1
        # yield_per_batch should be from mock (24), not from actual DB (12)
        assert results[0].yield_per_batch == mock_items_per_batch
        # units_needed should be 48 (as requested)
        assert results[0].units_needed == 48
