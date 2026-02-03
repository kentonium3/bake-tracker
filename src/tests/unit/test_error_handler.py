"""Unit tests for centralized error handler."""

import logging
import pytest
from unittest.mock import patch, MagicMock

from src.ui.utils.error_handler import handle_error, get_user_message
from src.services.exceptions import (
    ServiceError,
    IngredientNotFoundBySlug,
    IngredientNotFound,
    ProductNotFound,
    RecipeNotFound,
    PurchaseNotFound,
    InventoryItemNotFound,
    ValidationError,
    InsufficientStock,
    IngredientInUse,
    ProductInUse,
    SlugAlreadyExists,
    DatabaseError,
    CircularReferenceError,
    MaxDepthExceededError,
    NonLeafIngredientError,
    PlanStateError,
)


class TestGetUserMessage:
    """Tests for exception to user message mapping."""

    def test_ingredient_not_found_by_slug(self):
        exc = IngredientNotFoundBySlug("flour")
        title, msg = get_user_message(exc, "Get ingredient")
        assert title == "Not Found"
        assert "flour" in msg
        assert "IngredientNotFoundBySlug" not in msg  # No class names

    def test_ingredient_not_found(self):
        exc = IngredientNotFound(123)
        title, msg = get_user_message(exc, "Get ingredient")
        assert title == "Not Found"
        assert "not found" in msg.lower()

    def test_product_not_found(self):
        exc = ProductNotFound(456)
        title, msg = get_user_message(exc, "Get product")
        assert title == "Not Found"
        assert "not found" in msg.lower()

    def test_recipe_not_found(self):
        exc = RecipeNotFound(789)
        title, msg = get_user_message(exc, "Get recipe")
        assert title == "Not Found"
        assert "not found" in msg.lower()

    def test_purchase_not_found(self):
        exc = PurchaseNotFound(101)
        title, msg = get_user_message(exc, "Get purchase")
        assert title == "Not Found"
        assert "not found" in msg.lower()

    def test_inventory_item_not_found(self):
        exc = InventoryItemNotFound(202)
        title, msg = get_user_message(exc, "Get inventory")
        assert title == "Not Found"
        assert "not found" in msg.lower()

    def test_validation_error_with_errors_list(self):
        exc = ValidationError(["Name is required", "Slug is invalid"])
        title, msg = get_user_message(exc, "Create ingredient")
        assert title == "Validation Error"
        assert "Name is required" in msg
        assert "Slug is invalid" in msg

    def test_validation_error_single_error(self):
        exc = ValidationError(["Email is required"])
        title, msg = get_user_message(exc, "Create user")
        assert title == "Validation Error"
        assert "Email is required" in msg

    def test_insufficient_stock(self):
        exc = InsufficientStock("flour", required=100, available=50)
        title, msg = get_user_message(exc, "Record production")
        assert title == "Insufficient Inventory"
        assert "flour" in msg
        assert "100" in msg
        assert "50" in msg

    def test_ingredient_in_use_with_dict_deps(self):
        deps = {"recipes": 3, "products": 2}
        exc = IngredientInUse("flour", deps)
        title, msg = get_user_message(exc, "Delete ingredient")
        assert title == "Cannot Delete"
        assert "3 recipe(s)" in msg
        assert "2 product(s)" in msg

    def test_ingredient_in_use_with_all_deps(self):
        deps = {"recipes": 5, "products": 3, "inventory_items": 12, "children": 2}
        exc = IngredientInUse("sugar", deps)
        title, msg = get_user_message(exc, "Delete ingredient")
        assert title == "Cannot Delete"
        assert "5 recipe(s)" in msg
        assert "3 product(s)" in msg
        assert "12 inventory item(s)" in msg
        assert "2 child ingredient(s)" in msg

    def test_product_in_use(self):
        deps = {"inventory_items": 10, "purchases": 5}
        exc = ProductInUse(123, deps)
        title, msg = get_user_message(exc, "Delete product")
        assert title == "Cannot Delete"
        # Should show dependency counts
        assert "10" in msg
        assert "5" in msg

    def test_slug_already_exists(self):
        exc = SlugAlreadyExists("flour")
        title, msg = get_user_message(exc, "Create ingredient")
        assert title == "Duplicate"
        assert "flour" in msg

    def test_database_error(self):
        exc = DatabaseError("Connection timeout")
        title, msg = get_user_message(exc, "Save data")
        assert title == "Database Error"
        assert "Connection timeout" not in msg  # Don't expose technical details
        assert "try again" in msg.lower()

    def test_circular_reference_error(self):
        exc = CircularReferenceError(123, 456)
        title, msg = get_user_message(exc, "Move ingredient")
        assert title == "Invalid Operation"
        assert "circular" in msg.lower()

    def test_max_depth_exceeded_error(self):
        exc = MaxDepthExceededError(123, 3, 2)
        title, msg = get_user_message(exc, "Move ingredient")
        assert title == "Invalid Operation"
        assert "2" in msg  # max level

    def test_non_leaf_ingredient_error_without_suggestions(self):
        exc = NonLeafIngredientError(123, "Dark Chocolate", "recipe")
        title, msg = get_user_message(exc, "Add ingredient")
        assert title == "Invalid Selection"
        assert "Dark Chocolate" in msg
        assert "leaf" in msg.lower()

    def test_non_leaf_ingredient_error_with_suggestions(self):
        exc = NonLeafIngredientError(123, "Dark Chocolate", "recipe", ["Semi-Sweet Chips", "Cocoa Powder"])
        title, msg = get_user_message(exc, "Add ingredient")
        assert title == "Invalid Selection"
        assert "Dark Chocolate" in msg
        assert "Semi-Sweet Chips" in msg
        assert "Cocoa Powder" in msg

    def test_plan_state_error(self):
        # Create a mock state with a value attribute
        class MockState:
            value = "locked"

        exc = PlanStateError(123, MockState(), "modify recipes")
        title, msg = get_user_message(exc, "Update plan")
        assert title == "Invalid Operation"
        assert "locked" in msg.lower()
        assert "modify recipes" in msg

    def test_generic_service_error_fallback(self):
        exc = ServiceError("Something failed")
        title, msg = get_user_message(exc, "Do something")
        assert title == "Error"
        assert "failed" in msg.lower()

    def test_service_error_404_fallback(self):
        exc = ServiceError("Not found")
        exc.http_status_code = 404
        title, msg = get_user_message(exc, "Get item")
        assert title == "Not Found"
        assert "not found" in msg.lower()

    def test_service_error_400_fallback(self):
        exc = ServiceError("Invalid input")
        exc.http_status_code = 400
        title, msg = get_user_message(exc, "Create item")
        assert title == "Validation Error"

    def test_service_error_409_fallback(self):
        exc = ServiceError("Conflict detected")
        exc.http_status_code = 409
        title, msg = get_user_message(exc, "Update item")
        assert title == "Conflict"

    def test_service_error_422_fallback(self):
        exc = ServiceError("Business rule violated")
        exc.http_status_code = 422
        title, msg = get_user_message(exc, "Process item")
        assert title == "Cannot Complete"

    def test_unexpected_exception(self):
        exc = RuntimeError("Unexpected!")
        title, msg = get_user_message(exc, "Do something")
        assert title == "Unexpected Error"
        assert "contact support" in msg.lower()
        assert "RuntimeError" not in msg  # No class names

    def test_no_python_exception_names_exposed(self):
        """Verify no exception class names leak to user messages."""
        exceptions = [
            IngredientNotFoundBySlug("test"),
            IngredientNotFound(123),
            ProductNotFound(456),
            ValidationError(["error"]),
            ServiceError("error"),
            RuntimeError("error"),
        ]
        for exc in exceptions:
            _, msg = get_user_message(exc, "Test")
            assert exc.__class__.__name__ not in msg


class TestHandleError:
    """Tests for handle_error function."""

    @patch("src.ui.utils.error_handler.messagebox")
    def test_shows_dialog_by_default(self, mock_msgbox):
        exc = IngredientNotFoundBySlug("flour")
        handle_error(exc, operation="Get ingredient")
        mock_msgbox.showerror.assert_called_once()

    @patch("src.ui.utils.error_handler.messagebox")
    def test_no_dialog_when_disabled(self, mock_msgbox):
        exc = IngredientNotFoundBySlug("flour")
        handle_error(exc, operation="Get ingredient", show_dialog=False)
        mock_msgbox.showerror.assert_not_called()

    @patch("src.ui.utils.error_handler.messagebox")
    def test_dialog_with_parent(self, mock_msgbox):
        exc = IngredientNotFoundBySlug("flour")
        mock_parent = MagicMock()
        handle_error(exc, parent=mock_parent, operation="Get ingredient")
        mock_msgbox.showerror.assert_called_once()
        # Check that parent was passed
        call_kwargs = mock_msgbox.showerror.call_args
        assert call_kwargs[1]["parent"] == mock_parent

    @patch("src.ui.utils.error_handler.messagebox")
    def test_returns_title_and_message(self, mock_msgbox):
        exc = IngredientNotFoundBySlug("flour")
        title, msg = handle_error(exc, operation="Get", show_dialog=False)
        assert title == "Not Found"
        assert "flour" in msg

    def test_logs_service_error(self, caplog):
        exc = ServiceError("test error", correlation_id="test-123")
        with caplog.at_level(logging.ERROR):
            handle_error(exc, operation="Test op", show_dialog=False)
        assert "test-123" in caplog.text
        assert "ServiceError" in caplog.text

    def test_logs_service_error_without_correlation(self, caplog):
        exc = ServiceError("test error")
        with caplog.at_level(logging.ERROR):
            handle_error(exc, operation="Test op", show_dialog=False)
        assert "no-correlation" in caplog.text

    def test_logs_unexpected_error_with_traceback(self, caplog):
        exc = RuntimeError("Boom!")
        with caplog.at_level(logging.ERROR):
            handle_error(exc, operation="Test op", show_dialog=False)
        assert "unexpected error" in caplog.text.lower()


class TestCorrelationIdLogging:
    """Tests for correlation ID in error logging."""

    def test_correlation_id_logged(self, caplog):
        exc = IngredientNotFoundBySlug("flour")
        exc.correlation_id = "corr-abc-123"
        with caplog.at_level(logging.ERROR):
            handle_error(exc, operation="Test", show_dialog=False)
        assert "corr-abc-123" in caplog.text

    def test_no_correlation_id_handled(self, caplog):
        exc = IngredientNotFoundBySlug("flour")
        # correlation_id is None by default
        with caplog.at_level(logging.ERROR):
            handle_error(exc, operation="Test", show_dialog=False)
        assert "no-correlation" in caplog.text


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_validation_errors(self):
        exc = ValidationError([])
        title, msg = get_user_message(exc, "Validate")
        assert title == "Validation Error"

    def test_ingredient_in_use_empty_deps(self):
        exc = IngredientInUse("flour", {})
        title, msg = get_user_message(exc, "Delete")
        assert title == "Cannot Delete"
        assert "other items" in msg

    def test_product_in_use_empty_deps(self):
        exc = ProductInUse(123, {})
        title, msg = get_user_message(exc, "Delete")
        assert title == "Cannot Delete"
        assert "other items" in msg

    @patch("src.ui.utils.error_handler.messagebox")
    def test_handle_error_with_none_parent(self, mock_msgbox):
        exc = ServiceError("test")
        handle_error(exc, parent=None, operation="Test")
        # Should call without parent kwarg or with implicit None handling
        mock_msgbox.showerror.assert_called_once()
