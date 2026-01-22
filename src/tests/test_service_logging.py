"""Tests for service layer structured logging.

These tests verify that production and assembly operations emit structured
log entries with appropriate context information.
"""

import logging
import pytest
from decimal import Decimal

from src.services.database import session_scope
from src.services import batch_production_service, assembly_service
from src.services.logging_utils import get_service_logger, log_operation
from src.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    FinishedUnit,
    FinishedGood,
    Composition,
)


class TestLoggingUtilities:
    """Tests for logging utility functions."""

    def test_get_service_logger_returns_logger(self):
        """get_service_logger returns a configured Logger instance."""
        logger = get_service_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "bake_tracker.services.test_module"

    def test_get_service_logger_extracts_module_name(self):
        """get_service_logger extracts module name from full path."""
        logger = get_service_logger("src.services.batch_production_service")
        assert logger.name == "bake_tracker.services.batch_production_service"

    def test_log_operation_logs_at_info_level(self, caplog):
        """log_operation logs at INFO level by default."""
        logger = get_service_logger("test")

        with caplog.at_level(logging.INFO):
            log_operation(
                logger,
                operation="test_op",
                outcome="success",
                entity_id=123,
            )

        assert "test_op: success" in caplog.text

    def test_log_operation_logs_at_custom_level(self, caplog):
        """log_operation respects custom log level."""
        logger = get_service_logger("test")

        with caplog.at_level(logging.DEBUG):
            log_operation(
                logger,
                operation="debug_op",
                outcome="debug_outcome",
                level=logging.DEBUG,
            )

        assert "debug_op: debug_outcome" in caplog.text

    def test_log_operation_includes_extra_context(self, caplog):
        """log_operation includes extra context in log records."""
        logger = get_service_logger("test")

        with caplog.at_level(logging.INFO):
            log_operation(
                logger,
                operation="context_test",
                outcome="success",
                recipe_id=42,
                actual_yield=24,
            )

        # Check that the log record has extra attributes
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.operation == "context_test"
        assert record.outcome == "success"
        assert record.recipe_id == 42
        assert record.actual_yield == 24


class TestBatchProductionLogging:
    """Tests for batch_production_service logging."""

    def test_check_can_produce_logs_insufficient(self, test_db, caplog):
        """Check function should log when production isn't possible due to no inventory."""
        # Create recipe but no inventory (no products/inventory items)
        with session_scope() as session:
            ingredient = Ingredient(
                slug="missing-ingredient-log",
                display_name="Missing Ingredient Log",
                category="Other",
                density_volume_value=Decimal("1.0"),
                density_volume_unit="cup",
                density_weight_value=Decimal("100.0"),
                density_weight_unit="g",
            )
            session.add(ingredient)
            session.flush()

            recipe = Recipe(
                name="Recipe Without Inventory Log",
                category="Test",
            )
            session.add(recipe)
            session.flush()

            recipe_ingredient = RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                quantity=Decimal("100"),
                unit="g",
            )
            session.add(recipe_ingredient)
            session.flush()
            recipe_id = recipe.id

        with caplog.at_level(logging.INFO, logger="bake_tracker.services"):
            with session_scope() as session:
                result = batch_production_service.check_can_produce(
                    recipe_id=recipe_id,
                    num_batches=1,
                    session=session,
                )

        assert not result["can_produce"]
        assert "check_can_produce" in caplog.text
        assert "insufficient" in caplog.text.lower()

    def test_check_can_produce_logs_debug_on_success(self, test_db, caplog):
        """Check function should log DEBUG when check passes (empty recipe)."""
        # Create a recipe with no ingredients - trivially can produce
        with session_scope() as session:
            recipe = Recipe(
                name="Empty Recipe For Log Test",
                category="Test",
            )
            session.add(recipe)
            session.flush()
            recipe_id = recipe.id

        with caplog.at_level(logging.DEBUG, logger="bake_tracker.services"):
            with session_scope() as session:
                result = batch_production_service.check_can_produce(
                    recipe_id=recipe_id,
                    num_batches=1,
                    session=session,
                )

        assert result["can_produce"]
        # DEBUG log for successful check
        assert "Production check passed" in caplog.text


class TestAssemblyLogging:
    """Tests for assembly_service logging."""

    @pytest.fixture
    def setup_assembly_data(self, test_db):
        """Set up test data for assembly logging tests."""
        with session_scope() as session:
            # Create a recipe (required for FinishedUnit)
            recipe = Recipe(
                name="Assembly Cookie Log",
                category="Cookies",
            )
            session.add(recipe)
            session.flush()

            # Create finished unit with inventory
            finished_unit = FinishedUnit(
                recipe_id=recipe.id,
                slug="cookie-log-test",
                display_name="Cookie Log",
                items_per_batch=12,
                inventory_count=24,  # Pre-set inventory for assembly
            )
            session.add(finished_unit)
            session.flush()

            # Create finished good (the assembly target)
            finished_good = FinishedGood(
                slug="cookie-box-log-test",
                display_name="Cookie Box Log",
                inventory_count=0,
            )
            session.add(finished_good)
            session.flush()

            # Create composition (FU -> FG)
            composition = Composition(
                assembly_id=finished_good.id,
                finished_unit_id=finished_unit.id,
                component_quantity=12,  # 12 cookies per box
            )
            session.add(composition)

            return {
                "finished_unit_id": finished_unit.id,
                "finished_good_id": finished_good.id,
            }

    def test_record_assembly_logs_success(self, test_db, setup_assembly_data, caplog):
        """Assembly recording should log success with run ID."""
        data = setup_assembly_data

        with caplog.at_level(logging.INFO, logger="bake_tracker.services"):
            with session_scope() as session:
                result = assembly_service.record_assembly(
                    finished_good_id=data["finished_good_id"],
                    quantity=1,
                    session=session,
                )

        # Verify log contains key fields
        assert "record_assembly" in caplog.text
        assert "success" in caplog.text

        # Verify structured context
        success_records = [r for r in caplog.records if "success" in r.getMessage()]
        assert len(success_records) >= 1
        record = success_records[0]
        assert hasattr(record, "assembly_run_id")
        assert record.assembly_run_id == result["assembly_run_id"]

    def test_record_assembly_logs_debug_on_entry(self, test_db, setup_assembly_data, caplog):
        """Assembly recording should log DEBUG on function entry."""
        data = setup_assembly_data

        with caplog.at_level(logging.DEBUG, logger="bake_tracker.services"):
            with session_scope() as session:
                assembly_service.record_assembly(
                    finished_good_id=data["finished_good_id"],
                    quantity=1,
                    session=session,
                )

        # Should have a DEBUG entry log
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_records) >= 1
        assert "Recording assembly" in caplog.text

    def test_check_can_assemble_logs_insufficient(self, test_db, caplog):
        """Check function should log when assembly isn't possible."""
        # Create FG with FU component but no FU inventory
        with session_scope() as session:
            # Recipe for FU (needed for FU creation)
            recipe = Recipe(name="Empty Recipe Log", category="Test")
            session.add(recipe)
            session.flush()

            # FU with zero inventory
            fu = FinishedUnit(
                recipe_id=recipe.id,
                slug="empty-unit-log-test",
                display_name="Empty Unit Log",
                items_per_batch=1,
                inventory_count=0,
            )
            session.add(fu)
            session.flush()

            # FG that requires the FU
            fg = FinishedGood(slug="needs-components-log-test", display_name="Needs Components Log", inventory_count=0)
            session.add(fg)
            session.flush()

            # Composition requiring 10 FUs
            comp = Composition(
                assembly_id=fg.id,
                finished_unit_id=fu.id,
                component_quantity=10,
            )
            session.add(comp)
            session.flush()
            fg_id = fg.id

        with caplog.at_level(logging.INFO, logger="bake_tracker.services"):
            with session_scope() as session:
                result = assembly_service.check_can_assemble(
                    finished_good_id=fg_id,
                    quantity=1,
                    session=session,
                )

        assert not result["can_assemble"]
        assert "check_can_assemble" in caplog.text
        assert "insufficient" in caplog.text.lower()

    def test_check_can_assemble_logs_debug_on_success(self, test_db, caplog):
        """Check function should log DEBUG when assembly can proceed."""
        # Create FG with FU that has sufficient inventory
        with session_scope() as session:
            recipe = Recipe(name="Sufficient Recipe Log", category="Test")
            session.add(recipe)
            session.flush()

            fu = FinishedUnit(
                recipe_id=recipe.id,
                slug="sufficient-unit-log-test",
                display_name="Sufficient Unit Log",
                items_per_batch=1,
                inventory_count=100,  # Plenty of inventory
            )
            session.add(fu)
            session.flush()

            fg = FinishedGood(slug="sufficient-fg-log-test", display_name="Sufficient FG Log", inventory_count=0)
            session.add(fg)
            session.flush()

            comp = Composition(
                assembly_id=fg.id,
                finished_unit_id=fu.id,
                component_quantity=1,
            )
            session.add(comp)
            session.flush()
            fg_id = fg.id

        with caplog.at_level(logging.DEBUG, logger="bake_tracker.services"):
            with session_scope() as session:
                result = assembly_service.check_can_assemble(
                    finished_good_id=fg_id,
                    quantity=1,
                    session=session,
                )

        assert result["can_assemble"]
        assert "Assembly check passed" in caplog.text
