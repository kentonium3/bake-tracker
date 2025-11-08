---
work_package_id: WP02
title: Implement Database Connectivity Testing
subtasks: [T008, T009, T010, T011, T012, T013, T014]
lane: planned
priority: P1
estimated_hours: 1.0
dependencies: [WP01]
created: 2025-11-08
---

# WP02: Implement Database Connectivity Testing

## Objective

Add database connection testing to `HealthCheckService` using the existing `session_scope()` context manager with timeout handling and proper status reporting.

## Implementation

Add `_check_database()` method to src/services/health_service.py:

```python
def _check_database(self) -> str:
    """
    Test database connectivity with timeout.

    Returns:
        "connected", "disconnected", or "timeout"
    """
    from src.services.database import session_scope
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy import text
    import signal

    def timeout_handler(signum, frame):
        raise TimeoutError("Database check timed out")

    try:
        # Set 3-second timeout (Unix/Linux)
        # Windows: use threading.Timer as alternative
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(3)

        with session_scope() as session:
            session.execute(text("SELECT 1"))

        signal.alarm(0)  # Cancel timeout
        return "connected"

    except TimeoutError:
        self._logger.warning("Database connection check timed out")
        return "timeout"
    except SQLAlchemyError as e:
        self._logger.error(f"Database connection failed: {e}")
        return "disconnected"
    except Exception as e:
        self._logger.error(f"Unexpected error checking database: {e}")
        return "disconnected"
```

Update `_health_check_loop()` to use it:
```python
db_status = self._check_database()
status_data["database"] = db_status
status_data["status"] = "online" if db_status == "connected" else "degraded"
```

## Definition of Done

- [ ] `_check_database()` method added
- [ ] Returns "connected" when database available
- [ ] Returns "disconnected" on SQLAlchemyError
- [ ] Returns "timeout" after 3 seconds
- [ ] Integrated into health check loop
- [ ] Errors logged appropriately
- [ ] Unit tests pass (WP06)
