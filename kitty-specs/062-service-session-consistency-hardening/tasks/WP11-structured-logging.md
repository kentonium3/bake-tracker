---
work_package_id: "WP11"
subtasks:
  - "T055"
  - "T056"
  - "T057"
  - "T058"
  - "T059"
title: "Structured Logging"
phase: "Phase 2 - Polish"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "93136"
review_status: ""
reviewed_by: ""
dependencies: ["WP08", "WP09"]
history:
  - timestamp: "2026-01-22T15:30:43Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP11 – Structured Logging

## Implementation Command

```bash
spec-kitty implement WP11 --base WP09
```

**Note**: Can run in parallel with WP10 after WP08/WP09 complete.

---

## Objectives & Success Criteria

Add structured logging to production and assembly operations for debugging multi-service transactions.

**Decision** (from plan.md): Python stdlib logging with structured context dict.

**Success Criteria**:
- [ ] Logger configured for production/assembly services
- [ ] Key operations log with context (entity IDs, outcomes)
- [ ] Log format supports structured parsing
- [ ] No performance impact on normal operation
- [ ] Tests verify log output contains expected fields

---

## Context & Constraints

**Spec Requirements** (FR-016, FR-017):
- Production operations MUST emit structured log entries
- Assembly operations MUST emit structured log entries
- Include: operation type, entity IDs, outcome

**Log Levels**:
- INFO: Operation outcomes (success/failure)
- DEBUG: Parameter details, intermediate values

---

## Subtasks & Detailed Guidance

### Subtask T055 – Define logging format and create logger setup

**Steps**:
1. Create or update logging configuration
2. Define structured format for service logs

**Example logger setup** (in `src/services/__init__.py` or dedicated module):

```python
"""Service layer logging configuration."""

import logging
from typing import Any, Dict


def get_service_logger(name: str) -> logging.Logger:
    """
    Get a logger configured for service operations.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(f"bake_tracker.services.{name}")


def log_operation(
    logger: logging.Logger,
    operation: str,
    outcome: str,
    **context: Any,
) -> None:
    """
    Log a service operation with structured context.

    Args:
        logger: Logger instance
        operation: Operation name (e.g., "record_production")
        outcome: Outcome (e.g., "success", "validation_failed", "error")
        **context: Additional context (entity IDs, etc.)

    Example:
        log_operation(
            logger,
            operation="record_production",
            outcome="success",
            production_run_id=123,
            recipe_id=45,
        )
    """
    extra = {
        "operation": operation,
        "outcome": outcome,
        **context,
    }
    logger.info(
        f"{operation}: {outcome}",
        extra=extra,
    )
```

**Files**: `src/services/__init__.py` or `src/services/logging_utils.py`

---

### Subtask T056 – Add logging to record_batch_production

**File**: `src/services/batch_production_service.py`

**Location**: `record_batch_production` function

**Steps**:
1. Import logger utilities
2. Add log at function entry (DEBUG)
3. Add log at successful completion (INFO)
4. Add log at error/validation failure (WARNING)

**Example**:
```python
from src.services import get_service_logger, log_operation

logger = get_service_logger(__name__)


def record_batch_production(
    recipe_id: int,
    finished_unit_id: int,
    num_batches: int,
    actual_yield: int,
    # ... other params
    session: Session,
) -> Dict[str, Any]:
    logger.debug(
        "Recording batch production",
        extra={
            "recipe_id": recipe_id,
            "finished_unit_id": finished_unit_id,
            "num_batches": num_batches,
        },
    )

    try:
        # ... existing implementation ...

        # After successful creation:
        log_operation(
            logger,
            operation="record_batch_production",
            outcome="success",
            production_run_id=run.id,
            recipe_id=recipe_id,
            actual_yield=actual_yield,
        )

        return result

    except InsufficientInventoryError as e:
        log_operation(
            logger,
            operation="record_batch_production",
            outcome="insufficient_inventory",
            recipe_id=recipe_id,
            ingredient=e.ingredient_slug,
        )
        raise

    except Exception as e:
        log_operation(
            logger,
            operation="record_batch_production",
            outcome="error",
            recipe_id=recipe_id,
            error=str(e),
        )
        raise
```

**Files**: `src/services/batch_production_service.py`

---

### Subtask T057 – Add logging to record_assembly

**File**: `src/services/assembly_service.py`

**Location**: `record_assembly` function

**Same pattern as T056**:
```python
logger = get_service_logger(__name__)

def record_assembly(...) -> Dict[str, Any]:
    logger.debug("Recording assembly", extra={...})

    try:
        # ... implementation ...
        log_operation(
            logger,
            operation="record_assembly",
            outcome="success",
            assembly_run_id=run.id,
            finished_good_id=finished_good_id,
        )
        return result

    except Exception as e:
        log_operation(
            logger,
            operation="record_assembly",
            outcome="error",
            error=str(e),
        )
        raise
```

**Files**: `src/services/assembly_service.py`

---

### Subtask T058 – Add logging to check functions

**Functions**:
- `batch_production_service.check_can_produce`
- `assembly_service.check_can_assemble`

**Log when**:
- Check passes (DEBUG - frequent)
- Check fails (INFO - actionable)

**Example**:
```python
def check_can_produce(
    recipe_id: int,
    num_batches: int,
    scale_factor: float = 1.0,
    session: Session,
) -> Dict[str, Any]:
    result = # ... existing check logic ...

    if result["can_produce"]:
        logger.debug(
            "Production check passed",
            extra={"recipe_id": recipe_id, "num_batches": num_batches},
        )
    else:
        log_operation(
            logger,
            operation="check_can_produce",
            outcome="insufficient",
            recipe_id=recipe_id,
            missing_ingredients=result.get("missing_ingredients", []),
        )

    return result
```

**Files**: `src/services/batch_production_service.py`, `src/services/assembly_service.py`

---

### Subtask T059 – Add test verifying log output

**Purpose**: Verify logs contain expected structured context.

```python
# src/tests/test_service_logging.py

import logging
from unittest.mock import patch

from src.services.database import session_scope
from src.services import batch_production_service


def test_record_production_logs_success(caplog):
    """Production recording should log success with run ID."""
    with caplog.at_level(logging.INFO):
        with session_scope() as session:
            # Assuming test fixtures exist
            result = batch_production_service.record_batch_production(
                recipe_id=1,
                finished_unit_id=1,
                num_batches=1,
                actual_yield=12,
                session=session,
            )

    # Verify log contains key fields
    assert "record_batch_production" in caplog.text
    assert "success" in caplog.text


def test_check_can_produce_logs_insufficient(caplog):
    """Check function should log when production isn't possible."""
    with caplog.at_level(logging.INFO):
        with session_scope() as session:
            result = batch_production_service.check_can_produce(
                recipe_id=999,  # Assuming no inventory
                num_batches=100,
                session=session,
            )

    if not result["can_produce"]:
        assert "insufficient" in caplog.text.lower()
```

**Files**: `src/tests/test_service_logging.py` (new)

---

## Test Strategy

```bash
./run-tests.sh src/tests/test_service_logging.py -v
./run-tests.sh -v  # Full run

# Manual verification
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from src.services.database import session_scope
from src.services import batch_production_service
# Run an operation and observe logs
"
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Log spam in production | Performance | Use appropriate log levels (DEBUG for verbose) |
| Sensitive data in logs | Security | Don't log passwords, only IDs |
| Missing context | Debug difficulty | Include key entity IDs consistently |

---

## Definition of Done Checklist

- [ ] Logger utility functions exist
- [ ] `record_batch_production` logs success/failure
- [ ] `record_assembly` logs success/failure
- [ ] Check functions log validation failures
- [ ] Tests verify log output
- [ ] No passwords/secrets logged

---

## Activity Log

- 2026-01-22T15:30:43Z – system – lane=planned – Prompt created.
- 2026-01-22T23:00:05Z – claude-opus – shell_pid=88079 – lane=doing – Started implementation via workflow command
- 2026-01-22T23:14:40Z – claude-opus – shell_pid=88079 – lane=for_review – All subtasks complete. Structured logging added to batch_production_service and assembly_service with 11 passing tests.
- 2026-01-22T23:22:01Z – claude-opus – shell_pid=93136 – lane=doing – Started review via workflow command
