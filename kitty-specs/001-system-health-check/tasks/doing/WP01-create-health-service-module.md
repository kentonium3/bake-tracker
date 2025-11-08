---
work_package_id: WP01
title: Create Health Service Module Structure
subtasks:
  - T001
  - T002
  - T003
  - T004
  - T005
  - T006
  - T007
lane: planned
priority: P1
estimated_hours: 0.75
dependencies: []
created: 2025-11-08
history:
  - date: 2025-11-08
    action: Created
    agent: Claude Code
---

# WP01: Create Health Service Module Structure

## Objective

Create the foundational `HealthCheckService` class in `src/services/health_service.py` with threading infrastructure, initialization, start/stop methods, and the main health check loop. This establishes the skeleton that subsequent work packages will build upon.

## Context

**Feature**: System Health Check (001-system-health-check)
**Architecture**: Background service using daemon thread for periodic health checks
**Pattern**: Service layer component following existing BakeTracker architecture

**Key Architectural Decisions from Plan**:
- Use daemon thread (auto-terminates with application)
- Use `threading.Event` for clean shutdown signaling
- 30-second update interval via `event.wait(timeout=30)`
- Health check loop runs continuously until stopped

**Related Documents**:
- Specification: `kitty-specs/001-system-health-check/spec.md`
- Implementation Plan: `kitty-specs/001-system-health-check/plan.md`
- Constitution: `.kittify/memory/constitution.md`

## Detailed Guidance

### T001-T002: File Creation and Class Structure

**Create**: `src/services/health_service.py`

**Module Docstring** (Google style):
```python
"""
Health Check Service - Background monitoring for application health status.

This module provides a background service that periodically writes system health
information to a JSON file for external monitoring tools. The service runs on a
daemon thread and checks database connectivity, application status, and version
information every 30 seconds.

Example usage:
    from src.services.health_service import HealthCheckService

    service = HealthCheckService()
    service.start()  # Begins background monitoring
    # ... application runs ...
    service.stop()   # Clean shutdown
"""
```

**Required Imports**:
```python
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

# For version reading (T029-T035 in WP05)
try:
    import tomllib  # Python 3.11+
except ImportError:
    import toml as tomllib  # Fallback
```

**Class Definition**:
```python
class HealthCheckService:
    """
    Background service for writing periodic health status to file.

    The service runs on a daemon thread and updates `data/health.json` every
    30 seconds with current application status, database connectivity, timestamp,
    and version information.

    Attributes:
        _check_interval: Seconds between health checks (default: 30)
        _health_file: Path to health status JSON file
        _stop_event: Threading event for signaling shutdown
        _thread: Background daemon thread
        _app_version: Cached application version from pyproject.toml
    """
```

### T003: Implement `__init__()` Method

**Initialization Logic**:
1. Set up logging
2. Define health file path (`data/health.json`)
3. Create threading Event for shutdown
4. Initialize thread variable (None until started)
5. Cache application version (WP05 will implement reading logic)
6. Create `data/` directory if it doesn't exist

**Implementation**:
```python
def __init__(self, check_interval: int = 30, health_file: Optional[Path] = None):
    """
    Initialize the health check service.

    Args:
        check_interval: Seconds between health checks (default: 30)
        health_file: Custom path for health status file (default: data/health.json)
    """
    self._logger = logging.getLogger(__name__)
    self._check_interval = check_interval
    self._health_file = health_file or Path("data/health.json")
    self._stop_event = threading.Event()
    self._thread: Optional[threading.Thread] = None
    self._app_version = "unknown"  # WP05 will populate this

    # Ensure data directory exists
    self._health_file.parent.mkdir(parents=True, exist_ok=True)

    self._logger.info(f"Health check service initialized (interval: {check_interval}s)")
```

### T004: Implement `start()` Method

**Start Logic**:
1. Check if already running (prevent duplicate threads)
2. Clear stop event
3. Create daemon thread targeting `_health_check_loop`
4. Start thread
5. Log startup

**Implementation**:
```python
def start(self) -> None:
    """
    Start the health check background service.

    Launches a daemon thread that performs periodic health checks. If the
    service is already running, this method does nothing.

    Raises:
        RuntimeError: If thread fails to start
    """
    if self._thread and self._thread.is_alive():
        self._logger.warning("Health check service is already running")
        return

    self._stop_event.clear()
    self._thread = threading.Thread(
        target=self._health_check_loop,
        name="HealthCheckThread",
        daemon=True  # Auto-terminates when main thread exits
    )
    self._thread.start()
    self._logger.info("Health check service started")
```

### T005: Implement `stop()` Method

**Stop Logic**:
1. Check if running
2. Signal stop event
3. Wait for thread to finish (with timeout)
4. Log shutdown

**Implementation**:
```python
def stop(self, timeout: float = 2.0) -> None:
    """
    Stop the health check background service.

    Signals the background thread to stop and waits for clean shutdown.

    Args:
        timeout: Maximum seconds to wait for thread termination (default: 2.0)
    """
    if not self._thread or not self._thread.is_alive():
        self._logger.info("Health check service is not running")
        return

    self._logger.info("Stopping health check service...")
    self._stop_event.set()
    self._thread.join(timeout=timeout)

    if self._thread.is_alive():
        self._logger.warning("Health check thread did not stop within timeout")
    else:
        self._logger.info("Health check service stopped")
```

### T006-T007: Implement `_health_check_loop()` Method

**Loop Logic**:
1. Run until stop event is set
2. Perform health check (stub for now, WP02-03 will implement)
3. Wait for interval or until stop event
4. Handle exceptions gracefully

**Implementation**:
```python
def _health_check_loop(self) -> None:
    """
    Main loop for periodic health checks (runs in background thread).

    Continuously performs health checks every `_check_interval` seconds
    until stop() is called. Uses Event.wait() with timeout for clean
    shutdown without polling.
    """
    self._logger.info("Health check loop started")

    while not self._stop_event.is_set():
        try:
            # Perform health check and write status
            # (WP02-03 will implement _check_database and _write_health_status)
            status_data = {
                "status": "starting",  # Placeholder - will be dynamic
                "database": "unknown",  # WP02 will implement
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "app_version": self._app_version,  # WP05 will populate
                "api_version": "v1"
            }

            # WP03 will implement _write_health_status(status_data)
            self._logger.debug(f"Health check performed: {status_data['status']}")

        except Exception as e:
            # Never crash the health check thread
            self._logger.error(f"Error during health check: {e}", exc_info=True)

        # Wait for interval or until stop signal
        # This allows clean shutdown without busy-waiting
        self._stop_event.wait(timeout=self._check_interval)

    self._logger.info("Health check loop stopped")
```

## Test Strategy

**Unit Tests Required** (WP06):
- Test `__init__` creates instance with correct attributes
- Test `start()` launches thread successfully
- Test `stop()` terminates thread within timeout
- Test duplicate start() is handled gracefully
- Test stop() on non-running service is safe
- Mock `_health_check_loop` to verify thread creation

**Manual Verification**:
1. Create service instance
2. Call start(), verify thread exists and is alive
3. Wait 2 seconds, call stop(), verify thread terminates
4. Check logs for startup/shutdown messages

## Definition of Done

**Code Quality**:
- [ ] File exists at `src/services/health_service.py`
- [ ] Module docstring complete (Google style)
- [ ] Class docstring with attributes documented
- [ ] All methods have docstrings with Args/Returns/Raises
- [ ] Type hints on all method signatures
- [ ] Passes black formatting (100 char line length)
- [ ] Passes mypy type checking

**Functionality**:
- [ ] `HealthCheckService` can be instantiated
- [ ] `start()` launches daemon thread without blocking
- [ ] `stop()` terminates thread within 2 seconds
- [ ] Thread runs `_health_check_loop()` method
- [ ] Loop waits 30 seconds between iterations
- [ ] `data/` directory created automatically on init
- [ ] No exceptions on startup or shutdown

**Constitutional Compliance**:
- [ ] Type safety: All type hints present
- [ ] Code quality: Follows existing service layer patterns
- [ ] Complexity: Methods are simple (cyclomatic complexity <10)
- [ ] Documentation: All public methods documented

**Risks & Mitigations**:
- **Risk**: Thread doesn't stop cleanly
  - **Mitigation**: Use Event.wait() with timeout, daemon thread auto-terminates
- **Risk**: Race condition on start/stop
  - **Mitigation**: Check thread.is_alive() before operations

## Reviewer Guidance

**Key Review Points**:
1. **Threading Safety**: Verify Event is used correctly for shutdown
2. **Daemon Thread**: Confirm `daemon=True` is set
3. **Error Handling**: Ensure exceptions in loop don't crash thread
4. **Logging**: Check all lifecycle events are logged
5. **Type Hints**: Verify all methods have proper type annotations

**Expected Files**:
- `src/services/health_service.py` (~100-150 lines with docstrings)

**Testing Verification**:
- Thread starts and stops cleanly
- No resource leaks (thread terminates properly)
- Logs show startup/shutdown events

## Implementation Notes

- This is the foundation for all other work packages
- Keep it simple - just threading infrastructure
- Database and file I/O come in WP02-03
- Version reading comes in WP05
- Focus on clean thread lifecycle management

**Next Work Package**: WP02 (Database Testing) or WP03 (File Writing) - can work in parallel
