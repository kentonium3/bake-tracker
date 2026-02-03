"""Unit tests for exception hierarchy.

Validates that all exceptions inherit from ServiceError and have
required attributes per F089 Error Handling Foundation.
"""

import importlib
import inspect
import pytest

from src.services.exceptions import ServiceError


def get_all_exception_classes():
    """Dynamically discover all exception classes in services."""
    exceptions = []

    # Get exceptions from main exceptions module
    from src.services import exceptions as exc_module
    for name, obj in inspect.getmembers(exc_module, inspect.isclass):
        if issubclass(obj, Exception) and obj.__module__ == exc_module.__name__:
            exceptions.append((name, obj))

    # Get exceptions from service modules that might define local exceptions
    service_modules = [
        'src.services.batch_production_service',
        'src.services.assembly_service',
        'src.services.production_service',
        'src.services.event_service',
        'src.services.planning.planning_service',
        'src.services.package_service',
        'src.services.packaging_service',
        'src.services.finished_good_service',
        'src.services.finished_unit_service',
        'src.services.composition_service',
        'src.services.material_consumption_service',
        'src.services.fk_resolver_service',
        'src.services.recipient_service',
    ]

    for module_path in service_modules:
        try:
            module = importlib.import_module(module_path)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, Exception) and
                    obj.__module__ == module.__name__ and
                    name.endswith('Error')):
                    exceptions.append((name, obj))
        except ImportError:
            continue

    return exceptions


class TestExceptionHierarchy:
    """Verify all exceptions inherit from ServiceError."""

    @pytest.fixture
    def all_exceptions(self):
        return get_all_exception_classes()

    def test_all_domain_exceptions_inherit_from_service_error(self, all_exceptions):
        """All domain exceptions must inherit from ServiceError."""
        failures = []
        for name, exc_class in all_exceptions:
            # Skip ServiceError itself
            if exc_class is ServiceError:
                continue
            if not issubclass(exc_class, ServiceError):
                failures.append(f"{name} does not inherit from ServiceError")

        assert not failures, "Exceptions not inheriting from ServiceError:\n" + "\n".join(failures)

    def test_all_exceptions_have_http_status_code(self, all_exceptions):
        """All exceptions must have http_status_code attribute."""
        failures = []
        for name, exc_class in all_exceptions:
            if not hasattr(exc_class, 'http_status_code'):
                failures.append(f"{name} missing http_status_code")

        assert not failures, "Exceptions missing http_status_code:\n" + "\n".join(failures)

    def test_http_status_codes_are_valid(self, all_exceptions):
        """HTTP status codes must be valid (4xx or 5xx)."""
        valid_codes = [400, 404, 409, 422, 500]
        failures = []
        for name, exc_class in all_exceptions:
            if hasattr(exc_class, 'http_status_code'):
                code = exc_class.http_status_code
                if code not in valid_codes:
                    failures.append(f"{name} has invalid http_status_code: {code}")

        assert not failures, "Invalid http_status_codes:\n" + "\n".join(failures)


class TestServiceErrorBase:
    """Test ServiceError base class functionality."""

    def test_correlation_id_support(self):
        """ServiceError should accept correlation_id."""
        error = ServiceError("test", correlation_id="abc-123")
        assert error.correlation_id == "abc-123"

    def test_context_support(self):
        """ServiceError should accept context kwargs."""
        error = ServiceError("test", entity_id=123, slug="test-slug")
        assert error.context.get('entity_id') == 123
        assert error.context.get('slug') == "test-slug"

    def test_to_dict(self):
        """ServiceError should serialize to dict."""
        error = ServiceError("test message", correlation_id="abc")
        d = error.to_dict()
        assert d['type'] == 'ServiceError'
        assert d['message'] == 'test message'
        assert d['correlation_id'] == 'abc'
        assert d['http_status_code'] == 500

    def test_default_http_status_code(self):
        """ServiceError should default to 500."""
        assert ServiceError.http_status_code == 500

    def test_message_attribute(self):
        """ServiceError should store message attribute."""
        error = ServiceError("custom message")
        assert error.message == "custom message"

    def test_str_representation(self):
        """ServiceError string representation is the message."""
        error = ServiceError("error occurred")
        assert str(error) == "error occurred"


class TestSpecificExceptions:
    """Test specific exception classes."""

    def test_ingredient_not_found_by_slug(self):
        """IngredientNotFoundBySlug includes slug in message."""
        from src.services.exceptions import IngredientNotFoundBySlug
        error = IngredientNotFoundBySlug("all_purpose_flour")
        assert "all_purpose_flour" in str(error)
        assert error.http_status_code == 404
        assert error.slug == "all_purpose_flour"

    def test_validation_error(self):
        """ValidationError includes all error messages."""
        from src.services.exceptions import ValidationError
        error = ValidationError(["Name required", "Slug invalid"])
        assert "Name required" in str(error)
        assert "Slug invalid" in str(error)
        assert error.http_status_code == 400
        assert len(error.errors) == 2

    def test_insufficient_stock(self):
        """InsufficientStock includes all details."""
        from src.services.exceptions import InsufficientStock
        error = InsufficientStock("flour", required=100.0, available=50.0)
        assert error.ingredient_name == "flour"
        assert error.required == 100.0
        assert error.available == 50.0
        assert error.http_status_code == 422

    def test_ingredient_in_use(self):
        """IngredientInUse handles both dict and int deps."""
        from src.services.exceptions import IngredientInUse

        # Test with dict deps (new format)
        deps = {'recipes': 5, 'products': 3}
        error = IngredientInUse("flour", deps)
        assert error.http_status_code == 409
        assert "5 recipe(s)" in str(error)
        assert "3 product(s)" in str(error)

        # Test with int deps (legacy format)
        error_legacy = IngredientInUse("sugar", 10)
        assert "10 recipe(s)" in str(error_legacy)

    def test_database_error(self):
        """DatabaseError wraps original error."""
        from src.services.exceptions import DatabaseError
        original = Exception("Connection lost")
        error = DatabaseError("Connection failed", original_error=original)
        assert error.http_status_code == 500
        assert error.original_error == original

    def test_slug_already_exists(self):
        """SlugAlreadyExists includes slug."""
        from src.services.exceptions import SlugAlreadyExists
        error = SlugAlreadyExists("flour")
        assert "flour" in str(error)
        assert error.http_status_code == 409

    def test_plan_state_error(self):
        """PlanStateError includes context."""
        from src.services.exceptions import PlanStateError
        error = PlanStateError(123, "locked", "modify recipes")
        assert "123" in str(error)
        assert "locked" in str(error)
        assert "modify recipes" in str(error)
        assert error.http_status_code == 409


class TestHierarchyExceptions:
    """Test hierarchy-related exceptions."""

    def test_circular_reference_error(self):
        """CircularReferenceError provides context."""
        from src.services.exceptions import CircularReferenceError
        error = CircularReferenceError(123, 456)
        assert error.ingredient_id == 123
        assert error.new_parent_id == 456
        assert error.http_status_code == 422

    def test_max_depth_exceeded_error(self):
        """MaxDepthExceededError provides context."""
        from src.services.exceptions import MaxDepthExceededError
        error = MaxDepthExceededError(123, 4, 2)
        assert error.ingredient_id == 123
        assert error.would_be_level == 4
        assert error.max_level == 2
        assert error.http_status_code == 422

    def test_non_leaf_ingredient_error(self):
        """NonLeafIngredientError provides suggestions."""
        from src.services.exceptions import NonLeafIngredientError
        error = NonLeafIngredientError(
            123, "Chocolate", "recipe",
            suggestions=["Semi-Sweet Chips", "Dark Chocolate Bar"]
        )
        assert "Chocolate" in str(error)
        assert "Semi-Sweet Chips" in str(error)
        assert error.http_status_code == 400
