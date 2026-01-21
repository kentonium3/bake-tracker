"""
Test session atomicity across multi-service operations.

Feature 060: Architecture Hardening - Service Boundaries & Session Management
Work Package: WP01 - Session Ownership Foundation
Subtask: T001

This test module verifies that:
1. Multiple service operations using a shared session commit together
2. Failures in any service operation cause all changes to roll back
3. Session passthrough to downstream services is correctly implemented
4. The anti-pattern (nested session_scope) causes object detachment

These tests establish the foundational infrastructure for validating
session atomicity guarantees across the entire service layer.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from src.services.database import session_scope
from src.services import batch_production_service
from src.services import inventory_item_service
from src.services import recipe_service
from src.models import Recipe, Ingredient, FinishedUnit, InventoryItem
from src.models import Product, RecipeIngredient
from src.models.finished_unit import YieldMode


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def production_setup(test_db):
    """
    Set up a complete production scenario for atomicity testing.

    Creates:
    - Ingredient (flour)
    - Product (5 lb flour bag)
    - Inventory item (purchased flour)
    - Recipe using the ingredient (via RecipeIngredient)
    - Finished unit for the recipe

    Returns a dict with all created entities for test access.
    """
    session = test_db()

    # Create ingredient
    ingredient = Ingredient(
        display_name="Session Test Flour",
        slug="session-test-flour",
        category="Flour",
        density_volume_value=Decimal("1.0"),
        density_volume_unit="cup",
        density_weight_value=Decimal("120.0"),
        density_weight_unit="g",
    )
    session.add(ingredient)
    session.flush()

    # Create product
    product = Product(
        ingredient_id=ingredient.id,
        brand="Test Brand",
        package_size="5 lb",
        package_unit="lb",
        package_unit_quantity=Decimal("5.0"),
        preferred=True,
    )
    session.add(product)
    session.flush()

    # Create inventory item with substantial quantity
    # Note: InventoryItem doesn't have a 'unit' field - unit comes from Product.package_unit
    inventory_item = InventoryItem(
        product_id=product.id,
        quantity=10.0,  # 10 lbs of flour (in product's package_unit)
        purchase_date=date.today() - timedelta(days=1),
        unit_cost=2.50,  # $2.50 per lb
    )
    session.add(inventory_item)
    session.flush()

    # Create recipe (uses 'name' and 'category', not 'display_name')
    recipe = Recipe(
        name="Session Test Cookies",
        category="Cookies",
    )
    session.add(recipe)
    session.flush()

    # Create recipe ingredient (links recipe to ingredient with quantity)
    recipe_ingredient = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient.id,
        quantity=2.0,  # 2 cups flour per batch
        unit="cup",
    )
    session.add(recipe_ingredient)
    session.flush()

    # Create finished unit (yield info is now on FinishedUnit, not Recipe)
    finished_unit = FinishedUnit(
        recipe_id=recipe.id,
        display_name="Session Test Cookie Batch",
        slug="session-test-cookie-batch",
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=24,
        item_unit="cookies",
    )
    session.add(finished_unit)
    session.commit()

    # Store IDs and primitive values, NOT ORM objects
    # (ORM objects will be detached when the session closes)
    class SetupData:
        pass

    data = SetupData()
    # Store IDs for querying in tests
    data.ingredient_id = ingredient.id
    data.ingredient_slug = ingredient.slug
    data.product_id = product.id
    data.inventory_item_id = inventory_item.id
    data.recipe_id = recipe.id
    data.finished_unit_id = finished_unit.id
    data.session_factory = test_db

    return data


# =============================================================================
# Session Atomicity Tests
# =============================================================================


class TestMultiServiceAtomicity:
    """Test transaction atomicity across multiple service calls."""

    def test_shared_session_sees_uncommitted_changes(self, production_setup):
        """
        Verify that services using a shared session can see uncommitted changes.

        This is the fundamental requirement: when service A makes a change
        within a shared session, service B using the same session must see it
        before commit.
        """
        ingredient_slug = production_setup.ingredient_slug
        product_id = production_setup.product_id

        with session_scope() as session:
            # Query initial inventory
            initial_qty = session.query(InventoryItem).filter(
                InventoryItem.product_id == product_id
            ).first().quantity

            # Consume some inventory via service (with shared session)
            result = inventory_item_service.consume_fifo(
                ingredient_slug=ingredient_slug,
                quantity_needed=Decimal("1.0"),
                target_unit="lb",
                dry_run=False,
                session=session,
            )

            # Within same session, query should see the change (before commit)
            updated_item = session.query(InventoryItem).filter(
                InventoryItem.product_id == product_id
            ).first()

            assert updated_item.quantity < initial_qty, (
                "Uncommitted change should be visible within shared session"
            )

            # Rollback to verify nothing was auto-committed
            session.rollback()

        # After rollback, verify inventory restored
        with session_scope() as session:
            restored_item = session.query(InventoryItem).filter(
                InventoryItem.product_id == product_id
            ).first()
            assert restored_item.quantity == 10.0, (
                "Inventory should be restored after rollback"
            )

    def test_multi_service_rollback_on_failure(self, production_setup):
        """
        Verify that failures cause rollback across all service operations.

        When a transaction fails, ALL changes made by ALL services within
        that transaction must be rolled back, not just the failing operation.
        """
        ingredient_slug = production_setup.ingredient_slug
        product_id = production_setup.product_id

        initial_qty = 10.0

        try:
            with session_scope() as session:
                # First operation: consume inventory (succeeds)
                result = inventory_item_service.consume_fifo(
                    ingredient_slug=ingredient_slug,
                    quantity_needed=Decimal("1.0"),
                    target_unit="lb",
                    dry_run=False,
                    session=session,
                )

                # Verify consumption happened within session
                item = session.query(InventoryItem).filter(
                    InventoryItem.product_id == product_id
                ).first()
                assert item.quantity == 9.0

                # Force a failure that triggers rollback
                raise ValueError("Simulated failure after first operation")
        except ValueError:
            pass  # Expected

        # Verify ALL changes rolled back
        with session_scope() as session:
            restored_item = session.query(InventoryItem).filter(
                InventoryItem.product_id == product_id
            ).first()
            assert restored_item.quantity == initial_qty, (
                "Inventory consumption should be rolled back on transaction failure"
            )

    def test_session_passthrough_to_downstream_services(self, production_setup):
        """
        Verify that services pass session to downstream service calls.

        batch_production_service.record_batch_production() calls:
        - inventory_item_service.consume_fifo()
        - recipe_service.get_aggregated_ingredients()

        All must use the same session for atomicity.
        """
        recipe_id = production_setup.recipe_id
        finished_unit_id = production_setup.finished_unit_id
        product_id = production_setup.product_id

        with session_scope() as session:
            # Record production with shared session
            result = batch_production_service.record_batch_production(
                recipe_id=recipe_id,
                finished_unit_id=finished_unit_id,
                num_batches=1,
                actual_yield=24,
                session=session,
            )

            # Verify production was recorded (returns production_run_id on success)
            assert result["production_run_id"] is not None

            # Inventory should be consumed (visible in same session)
            item = session.query(InventoryItem).filter(
                InventoryItem.product_id == product_id
            ).first()

            # Flour should be consumed (2 cups = ~0.53 lbs)
            assert item.quantity < 10.0, (
                "Inventory should be consumed by production"
            )

            # Rollback entire transaction
            session.rollback()

        # Verify everything rolled back
        with session_scope() as session:
            # Inventory restored
            item = session.query(InventoryItem).filter(
                InventoryItem.product_id == product_id
            ).first()
            assert item.quantity == 10.0, (
                "Inventory should be restored after rollback"
            )

            # Production run should not exist
            from src.models import ProductionRun
            runs = session.query(ProductionRun).filter(
                ProductionRun.recipe_id == recipe_id
            ).all()
            assert len(runs) == 0, (
                "Production run should not exist after rollback"
            )


class TestSessionOwnershipContract:
    """Test the session ownership contract: accept session=None, use if provided."""

    def test_service_accepts_session_parameter(self, test_db):
        """
        Verify key services accept optional session parameter.

        All compliant services must accept session=None and use the
        provided session when given.
        """
        # These services are documented as compliant in CLAUDE.md
        import inspect

        services_to_check = [
            (batch_production_service, "check_can_produce"),
            (batch_production_service, "record_batch_production"),
            (inventory_item_service, "consume_fifo"),
            (recipe_service, "get_aggregated_ingredients"),
        ]

        for service_module, method_name in services_to_check:
            method = getattr(service_module, method_name)
            sig = inspect.signature(method)

            assert "session" in sig.parameters, (
                f"{service_module.__name__}.{method_name}() must accept 'session' parameter"
            )

            param = sig.parameters["session"]
            assert param.default is None, (
                f"{service_module.__name__}.{method_name}() session param must default to None"
            )

    def test_standalone_call_manages_own_transaction(self, production_setup):
        """
        Verify that services manage their own transaction when session=None.

        Backward compatibility: standalone callers that don't pass session
        should still work and have their changes committed.
        """
        ingredient_slug = production_setup.ingredient_slug
        product_id = production_setup.product_id

        # Call without session (standalone mode)
        result = inventory_item_service.consume_fifo(
            ingredient_slug=ingredient_slug,
            quantity_needed=Decimal("1.0"),
            target_unit="lb",
            dry_run=False,
            session=None,  # Standalone - manages own transaction
        )

        # Verify consumption was committed
        with session_scope() as session:
            item = session.query(InventoryItem).filter(
                InventoryItem.product_id == product_id
            ).first()
            assert item.quantity == 9.0, (
                "Standalone call should commit its own transaction"
            )


class TestAntiPatternDocumentation:
    """
    Document the anti-pattern: nested session_scope causes transaction issues.

    These tests document the PROBLEM that the session ownership pattern solves.
    The key issues with nested sessions are:
    1. Independent commits - inner session commits don't roll back with outer
    2. Lost updates - outer session can overwrite inner session's changes
    3. Transaction boundary confusion - no true atomicity across services
    """

    def test_nested_session_scope_independent_commits(self, production_setup):
        """
        Document that nested session_scope commits independently.

        This is the ANTI-PATTERN we're preventing. When an inner function
        calls session_scope() and commits, that commit is PERMANENT even if
        the outer session later rolls back.

        This test documents the problem - it's NOT how code should be written.
        """
        product_id = production_setup.product_id

        try:
            with session_scope() as outer_session:
                # Query object in outer session
                item = outer_session.query(InventoryItem).filter(
                    InventoryItem.product_id == product_id
                ).first()

                original_qty = item.quantity  # 10.0

                # ANTI-PATTERN: Inner function uses its own session_scope
                # This is what happens if a service doesn't accept session param
                def inner_operation_without_session_passthrough():
                    with session_scope() as inner_session:
                        # Inner session is a DIFFERENT transaction
                        inner_item = inner_session.query(InventoryItem).filter(
                            InventoryItem.product_id == product_id
                        ).first()
                        inner_item.quantity -= 1.0
                        # Inner session commits on exit - THIS IS THE PROBLEM!

                inner_operation_without_session_passthrough()

                # Now simulate a failure in the outer transaction
                # In a proper atomic transaction, this should roll back EVERYTHING
                raise ValueError("Simulated failure after inner operation")
        except ValueError:
            pass  # Expected

        # THE PROBLEM: Inner session's change was committed PERMANENTLY
        # even though the outer "transaction" failed!
        # With proper session passthrough, everything would have rolled back.
        with session_scope() as session:
            final_item = session.query(InventoryItem).filter(
                InventoryItem.product_id == product_id
            ).first()

            # Inner session committed independently - this is the anti-pattern!
            # Quantity is 9.0 (inner change persisted) not 10.0 (rolled back)
            assert final_item.quantity == 9.0, (
                "Inner session committed independently - anti-pattern demonstrated! "
                "Without session passthrough, inner commits are not atomic with outer."
            )


# =============================================================================
# Audit Results (T003)
# =============================================================================

"""
Service Compliance Audit - Session Ownership Pattern

Audited: 2026-01-20 (Feature 060, WP01)

Services verified as COMPLIANT with session ownership pattern:

1. batch_production_service.py
   - Methods: check_can_produce(), record_batch_production()
   - Session param: YES
   - Conditional handling: YES (nullcontext pattern at lines 279-281)
   - Downstream passing: YES (consume_fifo, get_aggregated_ingredients)
   - No internal commit when session provided: YES
   - Status: COMPLIANT (Gold Standard)

2. assembly_service.py
   - Methods: check_can_assemble(), record_assembly()
   - Session param: YES
   - Conditional handling: YES (nullcontext pattern)
   - Downstream passing: YES
   - No internal commit when session provided: YES
   - Status: COMPLIANT

3. recipe_service.py
   - Methods: get_aggregated_ingredients()
   - Session param: YES
   - Conditional handling: YES
   - Downstream passing: YES (ingredient_service)
   - No internal commit when session provided: YES
   - Status: COMPLIANT

4. ingredient_service.py
   - Methods: get_ingredient()
   - Session param: YES
   - Conditional handling: YES
   - Downstream passing: N/A (leaf service)
   - No internal commit when session provided: YES
   - Status: COMPLIANT

5. inventory_item_service.py
   - Methods: consume_fifo()
   - Session param: YES
   - Conditional handling: YES (if/else pattern at lines 440-446)
   - Downstream passing: YES (get_ingredient)
   - No internal commit when session provided: YES
   - Status: COMPLIANT

All 5 foundational services are COMPLIANT with the session ownership pattern.
No deviations found that would block WP01 completion.
"""
