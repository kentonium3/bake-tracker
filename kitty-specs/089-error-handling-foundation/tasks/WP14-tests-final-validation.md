---
work_package_id: WP14
title: Tests & Final Validation
lane: planned
dependencies:
- WP01
subtasks:
- T075
- T076
- T077
- T078
- T079
phase: Phase 3 - Validation
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-02T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP14 – Tests & Final Validation

## Implementation Command

```bash
spec-kitty implement WP14 --base WP12
```

**Depends on**: All previous WPs (validate complete implementation)

---

## Objectives & Success Criteria

**Objective**: Create exception hierarchy tests and validate pattern consistency across codebase.

**Success Criteria**:
- [ ] `src/tests/unit/test_exceptions.py` created
- [ ] All exceptions verified to inherit from ServiceError
- [ ] All exceptions have http_status_code attribute
- [ ] No unlogged generic Exception catches remain
- [ ] Full test suite passes

---

## Context & Constraints

**Test Location**: `src/tests/unit/test_exceptions.py`

**Validation Approach**:
1. Dynamic discovery of exception classes
2. Automated inheritance checking
3. Grep-based pattern detection for remaining anti-patterns

---

## Subtasks & Detailed Guidance

### Subtask T075 – Create test_exceptions.py

**Purpose**: Create test file for exception hierarchy validation.

**Steps**:
1. Create `src/tests/unit/test_exceptions.py`:

```python
"""Unit tests for exception hierarchy.

Validates that all exceptions inherit from ServiceError and have
required attributes per F089 Error Handling Foundation.
"""

import importlib
import inspect
import pkgutil
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

    # Get exceptions from service modules
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

    def test_all_exceptions_inherit_from_service_error(self, all_exceptions):
        """All domain exceptions must inherit from ServiceError."""
        failures = []
        for name, exc_class in all_exceptions:
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
```

**Files**: `src/tests/unit/test_exceptions.py`

### Subtask T076 – Test All Exceptions Inherit from ServiceError

**Purpose**: Run the inheritance tests.

**Steps**:
1. Run: `./run-tests.sh src/tests/unit/test_exceptions.py -v`
2. Fix any failures found

### Subtask T077 – Test http_status_code Attributes

**Purpose**: Verify all exceptions have proper HTTP codes.

**Steps**:
1. Tests in T075 cover this
2. Review any failures and fix

### Subtask T078 – Validate No Unlogged Generic Catches

**Purpose**: Find remaining anti-patterns in codebase.

**Steps**:
1. Run grep to find potential issues:

```bash
# Find except Exception without handle_error
grep -rn "except Exception" src/ui/ | grep -v "handle_error" | grep -v ".pyc"

# Find bare except
grep -rn "except:" src/ | grep -v ".pyc" | grep -v "# noqa"
```

2. Review results and either:
   - Fix if legitimate issue
   - Add `# noqa: E722` comment if intentional bare except

3. Document any intentional exceptions in comments

### Subtask T079 – Run Full Test Suite

**Purpose**: Ensure no regressions from error handling changes.

**Steps**:
1. Run full test suite: `./run-tests.sh -v`
2. Fix any failures
3. Verify coverage hasn't decreased significantly

---

## Definition of Done Checklist

- [ ] `test_exceptions.py` created and passes
- [ ] All exceptions inherit from ServiceError
- [ ] All exceptions have valid http_status_code
- [ ] Grep check shows no unhandled generic catches (or documented exceptions)
- [ ] Full test suite passes
- [ ] No regressions introduced

---

## Review Guidance

**Key Checkpoints**:
1. Run test suite yourself: `./run-tests.sh src/tests/unit/test_exceptions.py -v`
2. Run grep checks and verify results
3. Confirm no test failures

---

## Activity Log

- 2026-02-02T00:00:00Z – system – lane=planned – Prompt created.
